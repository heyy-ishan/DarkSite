import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import ViTModel, RobertaModel


# ============================================================================
# STRUCTURAL BRANCH — MLP for hand-crafted features
# ============================================================================

class StructuralBranch(nn.Module):
    
    #Processes the 24 hand-crafted structural features from scraper metadata.
    #Projects them to the same 768-dim space as ViT and RoBERTa for fusion.
    
    def __init__(self, input_dim=24, hidden_dim=256, output_dim=768, dropout=0.3):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim),
            nn.LayerNorm(output_dim),
        )

    def forward(self, x):
        """
        Args:
            x: Tensor [batch, 24]
        Returns:
            Tensor [batch, 768]
        """
        return self.network(x)


# ============================================================================
# CROSS-MODAL ATTENTION FUSION
# ============================================================================

class CrossModalAttention(nn.Module):
    
    #Fuses the three modality feature vectors using multi-head attention.
    
    #The three modality embeddings are treated as a sequence of 3 tokens.
    #Self-attention learns which modalities to attend to for each prediction.

    def __init__(self, embed_dim=768, num_heads=8, dropout=0.1):
        super().__init__()

        # Learnable modality type embeddings (like position embeddings)
        self.modality_embeddings = nn.Embedding(3, embed_dim)

        # Multi-head self-attention over the 3 modality tokens
        self.attention = nn.MultiheadAttention(
            embed_dim=embed_dim,
            num_heads=num_heads,
            dropout=dropout,
            batch_first=True,
        )

        self.norm1 = nn.LayerNorm(embed_dim)
        self.norm2 = nn.LayerNorm(embed_dim)

        # Feed-forward after attention
        self.ffn = nn.Sequential(
            nn.Linear(embed_dim, embed_dim * 4),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(embed_dim * 4, embed_dim),
            nn.Dropout(dropout),
        )

    def forward(self, visual_feat, text_feat, structural_feat, key_padding_mask=None):
        """
        Args:
            visual_feat, text_feat, structural_feat: [batch, 768]
            key_padding_mask: optional [batch, 3] bool. True = ignore (disabled modality).
        Returns:
            fused [batch, 768], attn_weights [batch, 3, 3] (averaged over heads)
        """
        batch_size = visual_feat.size(0)

        # Stack into sequence: [batch, 3, 768]
        sequence = torch.stack([visual_feat, text_feat, structural_feat], dim=1)

        # Add modality type embeddings
        modality_ids = torch.arange(3, device=sequence.device).unsqueeze(0).expand(batch_size, -1)
        sequence = sequence + self.modality_embeddings(modality_ids)

        # Self-attention with optional key_padding_mask (masked tokens contribute 0)
        attended, attn_weights = self.attention(
            sequence, sequence, sequence,
            key_padding_mask=key_padding_mask,
            need_weights=True,
            average_attn_weights=True,
        )
        # Shape invariant: averaged head weights → [batch, 3, 3]
        assert attn_weights.shape == (batch_size, 3, 3), \
            f"attn_weights shape mismatch: {attn_weights.shape}"

        sequence = self.norm1(sequence + attended)
        sequence = self.norm2(sequence + self.ffn(sequence))

        # Pool: weighted mean over UNMASKED modality tokens
        if key_padding_mask is not None:
            keep = (~key_padding_mask).unsqueeze(-1).to(sequence.dtype)  # [batch, 3, 1]
            fused = (sequence * keep).sum(dim=1) / keep.sum(dim=1).clamp_min(1.0)
        else:
            fused = sequence.mean(dim=1)

        return fused, attn_weights


# ============================================================================
# CLASSIFICATION HEADS
# ============================================================================

class ClassificationHeads(nn.Module):
    
    #Three prediction heads on top of the fused representation:
    #1. Binary: has_dark_patterns (yes/no) — sigmoid
    #2. Multi-label: 11 dark pattern types — independent sigmoids
    #3. Severity: none/low/medium/high — softmax
    

    def __init__(self, input_dim=768, num_types=11, num_severity=4, dropout=0.2):
        super().__init__()

        # Shared bottleneck
        self.shared = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.LayerNorm(512),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # Binary head
        self.binary_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, 1),
        )

        # Multi-label head (11 types)
        self.type_head = nn.Sequential(
            nn.Linear(512, 256),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, num_types),
        )

        # Severity head (4 classes)
        self.severity_head = nn.Sequential(
            nn.Linear(512, 128),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(128, num_severity),
        )

    def forward(self, fused):

        # Args:
        #     fused: Tensor [batch, 768]

        # Returns:
        #     binary_logits: Tensor [batch, 1]
        #     type_logits: Tensor [batch, 11]
        #     severity_logits: Tensor [batch, 4]


        shared = self.shared(fused)

        binary_logits = self.binary_head(shared)
        type_logits = self.type_head(shared)
        severity_logits = self.severity_head(shared)

        return binary_logits, type_logits, severity_logits


# ============================================================================
# FULL MODEL
# ============================================================================

class DarkPatternDetector(nn.Module):

    # Multi-modal dark pattern detection model.

    # Combines ViT (visual), RoBERTa (text), and MLP (structural) branches
    # with cross-modal attention fusion and multi-task prediction heads.


    def __init__(
        self,
        vit_model_name="google/vit-base-patch16-224",
        roberta_model_name="roberta-base",
        num_structural_features=24,
        num_types=11,
        num_severity=4,
        embed_dim=768,
        freeze_backbone_layers=8,
        dropout=0.2,
        disable_branches=None,
    ):
        super().__init__()

        self.embed_dim = embed_dim
        self.disable_branches = set(disable_branches or [])

        # --- Visual branch: ViT ---
        if "visual" not in self.disable_branches:
            self.vit = ViTModel.from_pretrained(vit_model_name)
            self._freeze_vit_layers(freeze_backbone_layers)
        else:
            self.vit = None

        # --- Text branch: RoBERTa ---
        if "text" not in self.disable_branches:
            self.roberta = RobertaModel.from_pretrained(roberta_model_name)
            self._freeze_roberta_layers(freeze_backbone_layers)
        else:
            self.roberta = None

        # --- Structural branch: MLP ---
        if "structural" not in self.disable_branches:
            self.structural_branch = StructuralBranch(
                input_dim=num_structural_features,
                output_dim=embed_dim,
                dropout=dropout,
            )
        else:
            self.structural_branch = None

        # --- Fusion ---
        self.fusion = CrossModalAttention(
            embed_dim=embed_dim,
            num_heads=8,
            dropout=dropout,
        )

        # --- Classification heads ---
        self.heads = ClassificationHeads(
            input_dim=embed_dim,
            num_types=num_types,
            num_severity=num_severity,
            dropout=dropout,
        )

    def _freeze_vit_layers(self, num_layers):
        """Freeze the first `num_layers` of ViT encoder (out of 12)."""
        if self.vit is None:
            return
        for param in self.vit.embeddings.parameters():
            param.requires_grad = False
        for i, layer in enumerate(self.vit.encoder.layer):
            if i < num_layers:
                for param in layer.parameters():
                    param.requires_grad = False

    def _freeze_roberta_layers(self, num_layers):
        """Freeze the first `num_layers` of RoBERTa encoder (out of 12)."""
        if self.roberta is None:
            return
        for param in self.roberta.embeddings.parameters():
            param.requires_grad = False
        for i, layer in enumerate(self.roberta.encoder.layer):
            if i < num_layers:
                for param in layer.parameters():
                    param.requires_grad = False

    def forward(self, image, input_ids, attention_mask, structural):
        batch_size = image.size(0)
        device = image.device

        # Build per-modality disabled mask (True = ignored by fusion attention)
        disabled = [
            "visual" in self.disable_branches,
            "text" in self.disable_branches,
            "structural" in self.disable_branches,
        ]
        if any(disabled):
            key_padding_mask = torch.tensor(disabled, dtype=torch.bool, device=device)
            key_padding_mask = key_padding_mask.unsqueeze(0).expand(batch_size, -1)
        else:
            key_padding_mask = None

        # --- Branch 1: Visual (ViT) ---
        if self.vit is not None:
            vit_output = self.vit(pixel_values=image)
            visual_feat = vit_output.last_hidden_state[:, 0, :]
        else:
            visual_feat = torch.zeros(batch_size, self.embed_dim, device=device)

        # --- Branch 2: Text (RoBERTa) ---
        if self.roberta is not None:
            roberta_output = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
            text_feat = roberta_output.last_hidden_state[:, 0, :]
        else:
            text_feat = torch.zeros(batch_size, self.embed_dim, device=device)

        # --- Branch 3: Structural (MLP) ---
        if self.structural_branch is not None:
            structural_feat = self.structural_branch(structural)
        else:
            structural_feat = torch.zeros(batch_size, self.embed_dim, device=device)

        # --- Fusion (masks out disabled branches) ---
        fused, attn_weights = self.fusion(
            visual_feat, text_feat, structural_feat,
            key_padding_mask=key_padding_mask,
        )

        # --- Prediction ---
        binary_logits, type_logits, severity_logits = self.heads(fused)

        return {
            "binary_logits": binary_logits,
            "type_logits": type_logits,
            "severity_logits": severity_logits,
            "attention_weights": attn_weights,
        }

    def get_trainable_params(self):
        # Count trainable vs frozen parameters.
        trainable = sum(p.numel() for p in self.parameters() if p.requires_grad)
        total = sum(p.numel() for p in self.parameters())
        frozen = total - trainable
        return {
            "total": total,
            "trainable": trainable,
            "frozen": frozen,
            "trainable_pct": round(trainable / max(total, 1) * 100, 1),
        }

    def get_param_groups(self, lr_backbone=1e-5, lr_new=1e-4):
        # Get parameter groups with different learning rates.
        backbone_params = []
        new_params = []

        for name, param in self.named_parameters():
            if not param.requires_grad:
                continue
            if "vit" in name or "roberta" in name:
                backbone_params.append(param)
            else:
                new_params.append(param)

        groups = []
        if backbone_params:
            groups.append({"params": backbone_params, "lr": lr_backbone})
        if new_params:
            groups.append({"params": new_params, "lr": lr_new})
        return groups


# ============================================================================
# MULTI-TASK LOSS
# ============================================================================

class MultiTaskLoss(nn.Module):
    # Combined loss with learnable task weights (Kendall et al., 2018),
    # class weights for imbalanced labels, and confidence-based sample weighting.

    def __init__(self, type_pos_weights=None, severity_weights=None):
        super().__init__()
        self.log_var_binary = nn.Parameter(torch.zeros(1))
        self.log_var_types = nn.Parameter(torch.zeros(1))
        self.log_var_severity = nn.Parameter(torch.zeros(1))

        if type_pos_weights is not None:
            self.register_buffer("type_pos_weights", type_pos_weights)
        else:
            self.type_pos_weights = None

        if severity_weights is not None:
            self.register_buffer("severity_weights", severity_weights)
        else:
            self.severity_weights = None

    def forward(self, binary_logits, type_logits, severity_logits,
                binary_labels, type_labels, severity_labels,
                sample_weights=None):

        # Per-sample losses (reduction="none")
        loss_binary_unreduced = F.binary_cross_entropy_with_logits(
            binary_logits, binary_labels, reduction="none"
        )
        loss_types_unreduced = F.binary_cross_entropy_with_logits(
            type_logits, type_labels,
            pos_weight=self.type_pos_weights,
            reduction="none",
        )
        loss_severity_unreduced = F.cross_entropy(
            severity_logits, severity_labels.view(-1),
            weight=self.severity_weights,
            reduction="none",
        )

        # Apply confidence-based sample weights
        if sample_weights is not None:
            sw = sample_weights.view(-1, 1)  # [batch, 1]
            loss_binary_unreduced = loss_binary_unreduced * sw
            loss_types_unreduced = loss_types_unreduced * sw
            loss_severity_unreduced = loss_severity_unreduced * sample_weights.view(-1)

        # Reduce to scalar
        loss_binary = loss_binary_unreduced.mean()
        loss_types = loss_types_unreduced.mean()
        loss_severity = loss_severity_unreduced.mean()

        # Uncertainty-based weighting (Kendall et al., 2018)
        # L_total = 0.5 * (1/sigma^2) * L_task + 0.5 * log(sigma^2)
        # With log_var = log(sigma^2): L_total = 0.5 * exp(-log_var) * L_task + 0.5 * log_var
        precision_binary = torch.exp(-self.log_var_binary)
        precision_types = torch.exp(-self.log_var_types)
        precision_severity = torch.exp(-self.log_var_severity)

        total_loss = (
            0.5 * precision_binary * loss_binary + 0.5 * self.log_var_binary +
            0.5 * precision_types * loss_types + 0.5 * self.log_var_types +
            0.5 * precision_severity * loss_severity + 0.5 * self.log_var_severity
        )

        loss_dict = {
            "total": total_loss.item(),
            "binary": loss_binary.item(),
            "types": loss_types.item(),
            "severity": loss_severity.item(),
            "weight_binary": precision_binary.item(),
            "weight_types": precision_types.item(),
            "weight_severity": precision_severity.item(),
        }

        return total_loss, loss_dict