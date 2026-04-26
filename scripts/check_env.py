import sys
print("python:", sys.version.split()[0])
try:
    import torch
    print("torch:", torch.__version__, "cuda:", torch.cuda.is_available())
    if torch.cuda.is_available():
        print("cuda_device:", torch.cuda.get_device_name(0))
except Exception as e:
    print("torch: MISSING", e)
try:
    import transformers
    print("transformers:", transformers.__version__)
except Exception as e:
    print("transformers: MISSING", e)
try:
    import sklearn
    print("sklearn:", sklearn.__version__)
except Exception as e:
    print("sklearn: MISSING", e)
try:
    import PIL
    print("pillow:", PIL.__version__)
except Exception as e:
    print("pillow: MISSING", e)
