#!/bin/bash
#SBATCH --job-name=llm_extract
#SBATCH --output=llm_extract_%j.log
#SBATCH --error=llm_extract_%j.err
#SBATCH --time=08:00:00
#SBATCH --nodelist=gpu01     # must match the node where the ollama server is running
#SBATCH --gres=gpu:1
#SBATCH --mem=8G
#SBATCH --cpus-per-task=4

# Add ollama to PATH
export PATH="/hpcnfs/scratch/SPE/ieo5660/local_LLM/bin:$PATH"

# model path for ollama
export OLLAMA_MODELS="/hpcnfs/home/ieo5660/scratch/ieo5660/local_LLM/models/"

# disable cloud features
export OLLAMA_NO_CLOUD=1

# must match the OLLAMA_HOST where the ollama server is running
export OLLAMA_HOST=127.0.0.1:11437

# activate mamba environment with ollama python client installed
# and additioanl required dependencies to run the script
source /hpcnfs/home/ieo5660/miniforge3/etc/profile.d/mamba.sh
mamba activate ollama 

python3 04-extract_llm.py

# test command to verify connectivity to ollama server
# curl http://localhost:11437/api/generate -d '{
#   "model": "qwen3.5:latest",
#   "prompt": "Why is the sky blue?"
# }' > response.json
