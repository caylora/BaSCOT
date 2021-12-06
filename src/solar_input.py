"""Contains functions to handle inputting and processing data."""
import numpy as np
import csv


def calculate_future_power_costs(current_price, rate, years):
    """Estimate costs based on current price, avg. growth rate, and time."""
    total = 0
    cost_list = []
    for i in range(years):
        total += current_price * pow(rate, i)
        cost_list.append(current_price * pow(rate, i))
    return total, cost_list


def read_pvwatts(file_name):
    """Retrieve energy information from pvwatts file."""
    with open(file_name, newline="") as data:
        # Define csv reader
        csv_reader = csv.reader(data)

        # Skip over header info
        for _ in range(18):
            next(csv_reader)

        # Define empty list
        solar_data = []

        # Iterate over remaining rows of data
        for row in csv_reader:
            # Convert value from W to kW, add to list
            solar_data.append(float(row[-1]) / 1000)

        # Fetch final total value from list
        total = solar_data.pop()

        # Convert from list to numpy array
        solar_data = np.array(solar_data)
        return (solar_data, total)


def read_usage(file_name):
    """Retrieve energy information from PennElec file."""
    with open(file_name, newline="") as data:
        # Define csv reader
        csv_reader = csv.reader(data)

        # Skip over header info
        for _ in range(6):
            next(csv_reader)

        # Define empty list
        usage_data = []

        # Iterate over remaining rows of data
        for row in csv_reader:
            # Add kWh values to list
            usage_data.append(float(row[-3]))

        # Convert list to numpy array
        usage_data = np.array(usage_data)
        total = np.sum(usage_data)
        return (usage_data, total)


def generate_constraints(data, n):
    """Given dataset, generate constraints in n-hour spans."""
    # Define empty numpy array of the same size as input
    constraints = np.empty_like(data)

    # Create a numpy array with starting values appended to end
    dummy = np.append(data, data[0 : (n - 2)])

    # Iterate over original range
    for i in range(len(data)):
        # Find sum of kWh for each n hour span
        constraints[i] = np.sum(dummy[i : (i + n)])
    return constraints
