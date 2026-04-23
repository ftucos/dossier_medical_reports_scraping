#!/bin/bash
#SBATCH --job-name=llm_extract
#SBATCH --output=logs/llm_extract_%j.log
#SBATCH --error=logs/llm_extract_%j.err
#SBATCH --time=08:00:00
#SBATCH --gres=gpu:1          # Request 1 GPU
#SBATCH --mem=40G             # Request 40GB RAM
#SBATCH --cpus-per-task=8

# === LOAD ENVIRONMENT ===
# activate mamba environment with ollama python client installed
# and additional required dependencies to run the script
source /hpcnfs/home/ieo5660/miniforge3/etc/profile.d/mamba.sh
mamba activate ollama 

module load CUDA/12.6.0

# Add ollama to PATH
export PATH="/hpcnfs/scratch/SPE/ieo5660/local_LLM/bin:$PATH"

# model path for ollama
export OLLAMA_MODELS="/hpcnfs/home/ieo5660/scratch/ieo5660/local_LLM/models/"

# disable cloud features
export OLLAMA_NO_CLOUD=1

# === OLLAMA START ===
# change port from 11434 default to avoid conflicting with other users on the same cluster
export OLLAMA_HOST=127.0.0.1:11437

# Run Ollama server in the background
# Start Ollama in background
ollama serve > logs/ollama_server_${SLURM_JOB_ID}.log 2>&1 &

# Wait until the server is responsive
echo "Waiting for Ollama to start on port $OLLAMA_HOST..."
until curl -s $OLLAMA_HOST > /dev/null 2>&1; do
    sleep 2
done
echo "Ollama is up!"

# === RUN EXTRACTION SCRIPT ===

python llm_extraction.py

