import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Prevents Qt-related errors
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

def parse_log_file(file_path):
    """
    Parses a log file to extract:
      - System time (as a datetime)
      - Logical clock values
      - Tick rate (from "Clock rate:")
      - Event type ("Sent", "Received", or "Internal")
      - Message queue length (if present in the line)
    """
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found, skipping...")
        return None, None
    
    system_times = []
    logical_clocks = []
    event_types = []
    queue_lengths = []
    
    tick_rate = None
    
    with open(file_path, "r") as f:
        for line in f:
            # Parse tick rate
            if "Clock rate:" in line:
                tick_rate = int(line.split(":")[1].strip().split()[0])
            
            # Only lines with "System time:" are real events
            if "System time:" in line:
                # --- 1) Extract system time and logical clock ---
                parts = line.split("|")
                # System time
                system_time_str = [p for p in parts if "System time:" in p][0].split(": ", 1)[1].strip()
                system_time = pd.to_datetime(system_time_str)
                # Logical clock
                logical_clock_str = [p for p in parts if "Logical Clock Time:" in p]
                if logical_clock_str:
                    logical_clock = int(logical_clock_str[0].split(": ")[1].strip())
                else:
                    logical_clock = None
                
                # --- 2) Determine event type ---
                # By checking the beginning of the line
                if line.startswith("Sent:"):
                    event_type = "Sent"
                elif line.startswith("Received:"):
                    event_type = "Received"
                elif line.startswith("Internal event"):
                    event_type = "Internal"
                else:
                    event_type = "Unknown"
                
                # --- 3) Parse message queue length (if present) ---
                if "Message Queue Length:" in line:
                    # E.g.: "... | Message Queue Length: 0"
                    q_len_str = line.split("Message Queue Length:")[1].strip().split()[0]
                    queue_length = int(q_len_str)
                else:
                    queue_length = None  # Not present in the line
                
                system_times.append(system_time)
                logical_clocks.append(logical_clock)
                event_types.append(event_type)
                queue_lengths.append(queue_length)
    
    # Build the DataFrame
    df = pd.DataFrame({
        "System Time": system_times,
        "Logical Clock": logical_clocks,
        "Event Type": event_types,
        "Message Queue Length": queue_lengths
    })
    # Sort by system time
    df = df.sort_values("System Time")
    
    return df, tick_rate

def plot_simulations(data, output_path, title, single_sim=False):
    """
    Generates and saves a plot for multiple or single simulations.
    Uses absolute system time (datetime) on the x-axis,
    and forces the axis to show HH:MM:SS formatting.
    """
    plt.figure(figsize=(12, 6))
    vm_colors = {"VM0": "blue", "VM1": "green", "VM2": "red"}
    
    for vm, simulations in data.items():
        color = vm_colors.get(vm, "black")
        for sim_index, df, tick_rate in simulations:
            label = f"{vm} Sim {sim_index} (Tick Rate: {tick_rate})" if tick_rate else f"{vm} Sim {sim_index}"
            marker_style = "o" if single_sim else None
            plt.plot(
                df["System Time"], 
                df["Logical Clock"], 
                label=label,
                color=color, 
                linestyle="-", 
                marker=marker_style, 
                markersize=3
            )
    
    # Format the x-axis to show only the time (HH:MM:SS)
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gcf().autofmt_xdate()  # Optional: rotates and aligns the date labels

    plt.xlabel("System Time")
    plt.ylabel("Logical Clock Time")
    plt.title(title)
    plt.legend(loc="upper center", fontsize=7)
    plt.grid(True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    print(f"Plot saved as {output_path}")

def process_all_simulations():
    """Processes all simulations across VMs, plots logical clock, and returns the data."""
    files = {vm: [f"logs/sim{i}_{vm.lower()}_log.txt" for i in range(1, 6)] for vm in ["VM0", "VM1", "VM2"]}
    data = {vm: [] for vm in files}
    
    for vm, file_list in files.items():
        for sim_index, file in enumerate(file_list, start=1):
            df, tick_rate = parse_log_file(file)
            if df is not None:
                data[vm].append((sim_index, df, tick_rate))
    
    # Generate a combined plot for all VMs
    plot_simulations(data, "img/all_vms_simulations_logical_clock_plot.png",
                     "Logical Clock Evolution Over System Time for All VMs and Simulations")
    
    # Return the data so we can do extra plots
    return data

def process_single_simulation(simulation_number):
    """Processes and plots logical clock evolution for a single simulation across VMs."""
    files = {vm: f"logs/sim{simulation_number}_{vm.lower()}_log.txt" for vm in ["VM0", "VM1", "VM2"]}
    data = {}
    
    for vm, file in files.items():
        df, tick_rate = parse_log_file(file)
        if df is not None:
            data[vm] = (df, tick_rate)
    
    if data:
        plot_simulations({vm: [(simulation_number, df, tick_rate)] for vm, (df, tick_rate) in data.items()},
                         f"img/single_sim{simulation_number}_logical_clock_plot.png", 
                         f"Logical Clock Evolution Over System Time for Single Simulation {simulation_number}",
                         single_sim=True)

def plot_queue_length_all_sims(data, output_path, title):
    """
    Generates and saves a single plot showing Message Queue Length over System Time
    for all simulations (sim1..simN) across all VMs (VM0, VM1, VM2).
    """
    plt.figure(figsize=(12, 6))
    vm_colors = {"VM0": "blue", "VM1": "green", "VM2": "red"}
    
    for vm, simulations in data.items():
        color = vm_colors.get(vm, "black")
        for sim_index, df, tick_rate in simulations:
            # Some lines may have NaN for queue length if not logged; drop them
            df_q = df.dropna(subset=["Message Queue Length"])
            if df_q.empty:
                continue
            label = f"{vm} Sim {sim_index} (Tick Rate: {tick_rate})"
            plt.plot(
                df_q["System Time"],
                df_q["Message Queue Length"],
                label=label,
                color=color,
                linestyle="-",
                marker=None
            )
    
    # Force HH:MM:SS formatting on x-axis
    ax = plt.gca()
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M:%S'))
    plt.gcf().autofmt_xdate()

    plt.xlabel("System Time")
    plt.ylabel("Message Queue Length")
    plt.title(title)
    plt.legend(loc="upper center", fontsize=7)
    plt.grid(True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    print(f"Plot saved as {output_path}")

def plot_event_counts_for_sim1(data, output_path, title):
    """
    Generates a bar chart showing the count of each event type
    (Sent, Received, Internal) for simulation #1 across all VMs,
    with the clock rate of each VM included in the x-axis labels.
    """
    # We want to handle VM0, VM1, VM2
    vms = ["VM0", "VM1", "VM2"]
    event_types = ["Sent", "Received", "Internal"]
    
    # Prepare a nested dict: counts[vm][event_type]
    counts = {vm: {et: 0 for et in event_types} for vm in vms}

    # Populate counts by filtering to sim_index == 1
    for vm in vms:
        for sim_index, df, tick_rate in data.get(vm, []):
            if sim_index == 1:
                # Count each event type in this DataFrame
                for et in event_types:
                    counts[vm][et] = (df["Event Type"] == et).sum()
    
    # Create a grouped bar chart
    x = np.arange(len(vms))  # positions for VM0, VM1, VM2
    width = 0.25
    
    plt.figure(figsize=(8, 6))
    for i, et in enumerate(event_types):
        # y-values are the counts for this event type across VMs
        y = [counts[vm][et] for vm in vms]
        # shift x by i*width for each event type
        plt.bar(x + i * width, y, width, label=et)
    
    # --- Minimal change: update x-axis labels to include clock rate ---
    vm_labels = []
    for vm in vms:
        tick_rate = None
        # Find simulation 1 data for the VM
        for sim_index, df, tr in data.get(vm, []):
            if sim_index == 1:
                tick_rate = tr
                break
        if tick_rate is not None:
            vm_labels.append(f"{vm}\n(Clock Rate: {tick_rate})")
        else:
            vm_labels.append(vm)
    
    plt.xticks(x + width, vm_labels)
    plt.xlabel("VM")
    plt.ylabel("Count of Events")
    plt.title(title)
    plt.legend()
    plt.grid(True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    print(f"Bar chart saved as {output_path}")

def main():
    # 1) Process logs and generate the usual logical clock plots
    data = process_all_simulations()
    
    # 2) Plot the message queue length (one plot for ALL VMs, ALL sims)
    plot_queue_length_all_sims(
        data,
        "img/all_vms_simulations_queue_length_plot.png",
        "Message Queue Length Over System Time for All VMs and Simulations"
    )
    
    # 3) Plot a bar chart for sim 1 event counts across all VMs
    plot_event_counts_for_sim1(
        data,
        "img/sim1_event_counts_bar_chart.png",
        "Event Counts for Sim 1 Across VMs"
    )
    
    # 4) Generate single simulation logical-clock plots
    process_single_simulation(1)

if __name__ == "__main__":
    main()
