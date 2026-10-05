import importlib.util

# Earlier material probes use PyTorch; the River CPU studies do not require it.
# Keep the earlier thread limit when that optional dependency is installed.
if importlib.util.find_spec("torch") is not None:
    import torch

    torch.set_num_threads(2)
