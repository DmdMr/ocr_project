#!/bin/bash

# Get the laptop model using system commands
laptop_model=$(system_profiler SPHardwareDataType | grep "Model Name")

# Get the RAM size using system commands
ram_size=$(system_profiler SPHardwareDataType | grep "Memory")

# Get the disk space usage using system commands
disk_usage=$(df -h /)

# Display the laptop model, RAM size, and disk usage
echo "Laptop Model: $laptop_model"
echo "RAM Size: $ram_size"
echo "Disk Usage: $disk_usage"