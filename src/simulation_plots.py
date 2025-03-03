import os
import pandas as pd
import matplotlib
matplotlib.use('Agg')  # Prevents Qt-related errors
import matplotlib.pyplot as plt

def parse_log_file(file_path):
    """
    Parses a log file to extract system time, logical clock values, and tick rate.
    """
    if not os.path.exists(file_path):
        print(f"Warning: {file_path} not found, skipping...")
        return None, None
    
    system_times = []
    logical_clocks = []
    tick_rate = None
    
    with open(file_path, "r") as f:
        for line in f:
            if "Clock rate:" in line:
                tick_rate = int(line.split(":")[1].strip().split()[0])
            
            if "Logical Clock Time:" in line:
                parts = line.split("|")
                system_time_str = [p for p in parts if "System time:" in p][0].split(": ", 1)[1].strip()
                system_time = pd.to_datetime(system_time_str)
                logical_clock = int([p for p in parts if "Logical Clock Time:" in p][0].split(": ")[1].strip())
                
                system_times.append(system_time)
                logical_clocks.append(logical_clock)
    
    df = pd.DataFrame({"System Time": system_times, "Logical Clock": logical_clocks})
    return df, tick_rate

def plot_simulations(data, output_path, title, single_sim=False):
    """
    Generates and saves a plot for multiple or single simulations.
    """
    plt.figure(figsize=(12, 6))
    vm_colors = {"VM0": "blue", "VM1": "green", "VM2": "red"}
    
    for vm, simulations in data.items():
        color = vm_colors.get(vm, "black")
        for sim_index, df, tick_rate in simulations:
            label = f"{vm} Sim {sim_index} (Tick Rate: {tick_rate})" if tick_rate else f"{vm} Sim {sim_index}"
            marker_style = "o" if single_sim else None  # Use markers only for single simulation
            plt.plot(df["System Time"], df["Logical Clock"], label=label, color=color, linestyle="-", marker=marker_style, markersize=3)
    
    plt.xlabel("System Time")
    plt.ylabel("Logical Clock Time")
    plt.title(title)
    plt.legend(loc="upper center", fontsize=7)
    plt.grid(True)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    plt.savefig(output_path)
    print(f"Plot saved as {output_path}")

def process_all_simulations():
    """Processes and plots logical clock evolution over system time for all simulations across VMs."""
    files = {vm: [f"logs/sim{i}_{vm.lower()}_log.txt" for i in range(1, 6)] for vm in ["VM0", "VM1", "VM2"]}
    data = {vm: [] for vm in files}
    
    for vm, file_list in files.items():
        for sim_index, file in enumerate(file_list, start=1):
            df, tick_rate = parse_log_file(file)
            if df is not None:
                data[vm].append((sim_index, df, tick_rate))
    
    for vm, simulations in data.items():
        if simulations:
            plot_simulations({vm: simulations}, f"img/{vm}_logical_clock_plot.png", f"Logical Clock Evolution Over System Time for {vm}")
    
    plot_simulations(data, "img/all_vms_simulations_logical_clock_plot.png", "Logical Clock Evolution Over System Time for All VMs and Simulations")

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

def main():
    """Main function to process all simulations and generate plots."""
    process_all_simulations()
    for sim_num in range(1, 6):
        process_single_simulation(sim_num)

if __name__ == "__main__":
    main()
