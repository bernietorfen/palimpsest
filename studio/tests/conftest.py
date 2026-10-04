import torch

# Small numerical probes run on the RunPod CPU; avoid spawning 120 BLAS threads.
torch.set_num_threads(2)
