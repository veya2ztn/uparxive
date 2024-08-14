#!/bin/bash

# Define the memory limit (in KB), replace <MEMORY_LIMIT> with your desired threshold
flag=$1

MEMORY_LIMIT=450000000

# Define the path to your batch script
BATCH_SCRIPT_PATH="/home/zhangtianning.di/projects/unique_data_build/bash_script/batch_tex_to_xml.sh"

# Define the argument for your batch script
BATCH_SCRIPT_ARG="/nvme/zhangtianning/datasets/whole_arxiv_data/whole_arxiv_all_files/analysis/fail_for_compiling.filelist $flag 1000"

ps -axuf | grep tex_to | awk '{print $2}' | xargs -n 1 kill;ps -axuf | grep latexml | awk '{print $2}' | xargs -n 1 kill -9;ps -axuf | grep python_script | awk '{print $2}' | xargs -n 1 kill -9
bash $BATCH_SCRIPT_PATH $BATCH_SCRIPT_ARG
echo "auto restart ==> $BATCH_SCRIPT_PATH $BATCH_SCRIPT_ARG"

# Function to check memory and execute commands if the limit is reached
check_memory_and_execute() {
    # Get the current memory usage
    current_memory=$(free | awk '/^Mem:/{print $3}')

    # Check if the current memory usage is greater than or equal to the limit
    if [ "$current_memory" -ge "$MEMORY_LIMIT" ]; then
        # Execute the commands
        ps -axuf | grep tex_to_xml | awk '{print $2}' | xargs -n 1 kill -9;ps -axuf | grep latexml | awk '{print $2}' | xargs -n 1 kill -9;ps -axuf | grep tail | awk '{print $2}' | xargs -n 1 kill -9
        bash $BATCH_SCRIPT_PATH $BATCH_SCRIPT_ARG
        echo "auto restart ==> $BATCH_SCRIPT_PATH $BATCH_SCRIPT_ARG"
    fi
}

# Main loop that checks memory usage at regular intervals
while true; do
    check_memory_and_execute
    # Sleep for a certain amount of time (e.g., 5 seconds) before checking again
    sleep 5
done