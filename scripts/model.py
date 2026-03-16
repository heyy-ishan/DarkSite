import torch
import torch.nn as nn
import torch.nn.functional as F
from transformers import ViTModel, RobertaModel


# ============================================================================
# STRUCTURAL BRANCH — MLP for hand-crafted features
# ============================================================================

class StructuralBranch(nn.Module):
    
    #Processes the 25 hand-crafted structural features from scraper metadata.
    #Projects them to the same 768-dim space as ViT and RoBERTa for fusion.
    
    def __init__(self, input_dim=25, hidden_dim=256, output_dim=768, dropout=0.3):
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
            x: Tensor [batch, 25]
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

    def forward(self, visual_feat, text_feat, structural_feat):
        
        #Args:
        #    visual_feat: Tensor [batch, 768]
        #    text_feat: Tensor [batch, 768]
        #    structural_feat: Tensor [batch, 768]
        
        #Returns:
        #    Tensor [batch, 768] — fused representation
        
        batch_size = visual_feat.size(0)

        # Stack into sequence: [batch, 3, 768]
        sequence = torch.stack([visual_feat, text_feat, structural_feat], dim=1)

        # Add modality type embeddings
        modality_ids = torch.arange(3, device=sequence.device).unsqueeze(0).expand(batch_size, -1)
        sequence = sequence + self.modality_embeddings(modality_ids)

        # Self-attention (transformer block)
        attended, attn_weights = self.attention(sequence, sequence, sequence)
        sequence = self.norm1(sequence + attended)
        sequence = self.norm2(sequence + self.ffn(sequence))

        # Pool: mean over the 3 modality tokens → single vector
        fused = sequence.mean(dim=1)  # [batch, 768]

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
        num_structural_features=25,
        num_types=11,
        num_severity=4,
        embed_dim=768,
        freeze_backbone_layers=8,
        dropout=0.2,
    ):
        super().__init__()

        self.embed_dim = embed_dim

        # --- Visual branch: ViT ---
        self.vit = ViTModel.from_pretrained(vit_model_name)
        # Freeze early layers, finetune later layers
        self._freeze_vit_layers(freeze_backbone_layers)

        # --- Text branch: RoBERTa ---
        self.roberta = RobertaModel.from_pretrained(roberta_model_name)
        # Freeze early layers
        self._freeze_roberta_layers(freeze_backbone_layers)

        # --- Structural branch: MLP ---
        self.structural_branch = StructuralBranch(
            input_dim=num_structural_features,
            output_dim=embed_dim,
            dropout=dropout,
        )

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
        # Freeze embeddings
        for param in self.vit.embeddings.parameters():
            param.requires_grad = False
        # Freeze first N encoder layers
        for i, layer in enumerate(self.vit.encoder.layer):
            if i < num_layers:
                for param in layer.parameters():
                    param.requires_grad = False

    def _freeze_roberta_layers(self, num_layers):
        """Freeze the first `num_layers` of RoBERTa encoder (out of 12)."""
        # Freeze embeddings
        for param in self.roberta.embeddings.parameters():
            param.requires_grad = False
        # Freeze first N encoder layers
        for i, layer in enumerate(self.roberta.encoder.layer):
            if i < num_layers:
                for param in layer.parameters():
                    param.requires_grad = False

    def forward(self, image, input_ids, attention_mask, structural):
       

        # Forward pass through all branches, fusion, and prediction heads.

        # Args:
        #     image: Tensor [batch, 3, 224, 224]
        #     input_ids: Tensor [batch, max_len]
        #     attention_mask: Tensor [batch, max_len]
        #     structural: Tensor [batch, 25]

        # Returns:
        #     dict with:
        #         binary_logits: Tensor [batch, 1]
        #         type_logits: Tensor [batch, 11]
        #         severity_logits: Tensor [batch, 4]
        #         attention_weights: Tensor [batch, num_heads, 3, 3]
       
        # --- Branch 1: Visual (ViT) ---
        # ViT outputs: last_hidden_state [batch, num_patches+1, 768]
        # Use the [CLS] token (index 0) as the image representation
        vit_output = self.vit(pixel_values=image)
        visual_feat = vit_output.last_hidden_state[:, 0, :]  # [batch, 768]

        # --- Branch 2: Text (RoBERTa) ---
        # RoBERTa outputs: last_hidden_state [batch, seq_len, 768]
        # Use the [CLS] token (index 0) as the text representation
        roberta_output = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
        text_feat = roberta_output.last_hidden_state[:, 0, :]  # [batch, 768]

        # --- Branch 3: Structural (MLP) ---
        structural_feat = self.structural_branch(structural)  # [batch, 768]

        # --- Fusion ---
        fused, attn_weights = self.fusion(visual_feat, text_feat, structural_feat)

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
            "trainable_pct": round(trainable / total * 100, 1),
        }

    def get_param_groups(self, lr_backbone=1e-5, lr_new=1e-4):
        # Get parameter groups with different learning rates.
        # Pre-trained layers get a lower LR, new layers get a higher LR.
        
        backbone_params = []
        new_params = []

        for name, param in self.named_parameters():
            if not param.requires_grad:
                continue
            if "vit" in name or "roberta" in name:
                backbone_params.append(param)
            else:
                new_params.append(param)

        return [
            {"params": backbone_params, "lr": lr_backbone},
            {"params": new_params, "lr": lr_new},
        ]


# ============================================================================
# MULTI-TASK LOSS
# ============================================================================

class MultiTaskLoss(nn.Module):
    
    #Combined loss for three tasks with learnable task weights.
    
    #Uses uncertainty-based weighting (Kendall et al., 2018) to automatically
    #balance the three losses during training.
    
    def __init__(self):
        super().__init__()
        # Learnable log-variance parameters for each task
        # Initialize to 0 (equal weighting)
        self.log_var_binary = nn.Parameter(torch.zeros(1))
        self.log_var_types = nn.Parameter(torch.zeros(1))
        self.log_var_severity = nn.Parameter(torch.zeros(1))

    def forward(self, binary_logits, type_logits, severity_logits,
                binary_labels, type_labels, severity_labels):

        # Compute weighted multi-task loss.

        # Args:
        #     binary_logits: [batch, 1]
        #     type_logits: [batch, 11]
        #     severity_logits: [batch, 4]
        #     binary_labels: [batch, 1]
        #     type_labels: [batch, 11]
        #     severity_labels: [batch, 1]

        # Returns:
        #     total_loss, loss_dict

        # Binary classification loss
        loss_binary = F.binary_cross_entropy_with_logits(binary_logits, binary_labels)

        # Multi-label classification loss
        loss_types = F.binary_cross_entropy_with_logits(type_logits, type_labels)

        # Severity classification loss
        loss_severity = F.cross_entropy(severity_logits, severity_labels.squeeze(1))

        # Uncertainty-based weighting:
        # L_total = (1/2σ²) * L_task + log(σ)
        # Using log-variance for numerical stability
        precision_binary = torch.exp(-self.log_var_binary)
        precision_types = torch.exp(-self.log_var_types)
        precision_severity = torch.exp(-self.log_var_severity)

        total_loss = (
            precision_binary * loss_binary + self.log_var_binary +
            precision_types * loss_types + self.log_var_types +
            precision_severity * loss_severity + self.log_var_severity
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