#!/bin/bash
#SBATCH --job-name=ollama_server
#SBATCH --output=ollama_server_%j.log
#SBATCH --error=ollama_server_%j.err
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1          # Request 1 GPU
#SBATCH --mem=40G             # Request 40GB RAM
#SBATCH --cpus-per-task=8

# === LOAD ENVIRONMENT ===
module load CUDA/12.6.0

# Add ollama to PATH
export PATH="/hpcnfs/scratch/SPE/ieo5660/local_LLM/bin:$PATH"

# model path for ollama
export OLLAMA_MODELS="/hpcnfs/home/ieo5660/scratch/ieo5660/local_LLM/models/"

# disable cloud features
export OLLAMA_NO_CLOUD=1

# === OPTIONAL OLLAMA START ===
# Run Ollama server in the background
export OLLAMA_HOST=127.0.0.1:11437

# run ollama
ollama serve 