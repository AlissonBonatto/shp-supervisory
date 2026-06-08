import pandas as pd
import matplotlib.pyplot as plt

def plot_system_data(file_path, percentage):
    if not (0 <= percentage <= 1):
        raise ValueError("Percentage must be between 0 and 1.")

    # Load the dataset
    df = pd.read_csv(file_path)

    # Calculate the number of rows to include
    limit_index = int(len(df) * percentage)
    subset = df.iloc[:limit_index]

    # Create the plot
    plt.figure(figsize=(10, 6))
    plt.plot(subset['time_s'], subset['position_cm'], label='Position ($cm$)')
    plt.plot(subset['time_s'], subset['setpoint_cm'], label='Setpoint ($cm$)', linestyle='--')

    plt.xlabel('Time ($s$)')
    plt.ylabel('Value ($cm$)')
    plt.title('Position vs Setpoint')
    plt.legend()
    plt.grid(True)
    plt.show()

# Example usage:
plot_system_data('./teste.csv', 0.8)