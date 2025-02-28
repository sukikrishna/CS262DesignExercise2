import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Prevents Qt-related errors
import matplotlib.pyplot as plt
import os

# File paths for logs (simulations 1-5 for each VM)
files = {
    "VM0": [f"logs/sim{i}_vm0_log.txt" for i in range(1, 6)],
    "VM1": [f"logs/sim{i}_vm1_log.txt" for i in range(1, 6)],
    "VM2": [f"logs/sim{i}_vm2_log.txt" for i in range(1, 6)]
}

# Dictionary to store extracted data for each VM across simulations
data = {vm: [] for vm in files}

# Parsing log files
for vm, file_list in files.items():
    for sim_index, file in enumerate(file_list, start=1):
        if not os.path.exists(file):
            print(f"Warning: {file} not found, skipping...")
            continue  # Skip missing files

        system_times = []
        logical_clocks = []
        tick_rate = None

        with open(file, "r") as f:
            for line in f:
                # Extract clock rate (ticks per second) from the header
                if "Clock rate:" in line:
                    tick_rate = int(line.split(":")[1].strip().split()[0])

                if "Logical Clock Time:" in line:
                    parts = line.split("|")

                    # Extract system time correctly
                    system_time_str = [p for p in parts if "System time:" in p][0].split(": ", 1)[1].strip()
                    system_time = pd.to_datetime(system_time_str)  # Convert to datetime

                    # Extract logical clock time
                    logical_clock = int([p for p in parts if "Logical Clock Time:" in p][0].split(": ")[1].strip())

                    system_times.append(system_time)
                    logical_clocks.append(logical_clock)

        # Store extracted data in a DataFrame
        df = pd.DataFrame({"System Time": system_times, "Logical Clock": logical_clocks})
        data[vm].append((sim_index, df, tick_rate))  # Store as (simulation number, dataframe, tick rate)

# Generate separate plots for each VM showing all available simulations
for vm, simulations in data.items():
    if not simulations:  # Skip if no data is available
        print(f"No data available for {vm}, skipping plot...")
        continue

    plt.figure(figsize=(12, 6))

    for sim_index, df, tick_rate in simulations:
        label = f"Sim {sim_index} (Tick Rate: {tick_rate})" if tick_rate else f"Sim {sim_index}"
        plt.plot(df["System Time"], df["Logical Clock"], label=label, marker="o", linestyle="-")

    plt.xlabel("System Time")
    plt.ylabel("Logical Clock Time")
    plt.title(f"Logical Clock Evolution Over System Time for {vm}")
    plt.legend()
    plt.grid(True)

    # Save each VM's plot separately
    plt.savefig(f"{vm}_logical_clock_plot.png")

print("Plots saved for available simulations of VM0, VM1, and VM2, including tick rates in the legend.")

# Generate a single plot for all simulations and VMs with consistent colors
plt.figure(figsize=(12, 6))

# Define colors for each VM
vm_colors = {
    "VM0": "blue",
    "VM1": "green",
    "VM2": "red"
}

# Plot all simulations for all VMs on one plot
for vm, simulations in data.items():
    color = vm_colors.get(vm, "black")  # Default to black if VM not in predefined colors
    
    for sim_index, df, tick_rate in simulations:
        label = f"{vm} Sim {sim_index} (Tick Rate: {tick_rate})" if tick_rate else f"{vm} Sim {sim_index}"
        plt.plot(df["System Time"], df["Logical Clock"], label=label, color=color, linestyle="-")

plt.xlabel("System Time")
plt.ylabel("Logical Clock Time")
plt.title("Logical Clock Evolution Over System Time for All VMs and Simulations")
plt.legend(loc="upper center", fontsize=7)
plt.grid(True)

# Save the single combined plot
plt.savefig("all_vms_simulations_logical_clock_plot.png")

print("Single plot for all VMs and simulations saved as 'all_vms_simulations_logical_clock_plot.png'.")
