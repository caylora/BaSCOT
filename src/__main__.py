"""Solve LP and MILP problems to optimize solar and battery capacity."""
import json
import time
from os.path import exists

import matplotlib.pyplot as plt
import numpy as np
from ortools.linear_solver import pywraplp

import solar_input as si

# ------------------ DATA ------------------ #
BIG_M = 1000000
MIN_CHARGE = 0.5
ARRAY_COST = 2710  # $/kW
TAX_MODIFIER = 0.74
BATTERY_COST = 341  # $/kWh
ENERGY_COST = 0.134  # current $/kWh
SYSTEM_LIFESPAN = 25  # yrs
ROOF_AREA = 30  # m^2
AREA_USAGE = 5.181  # m^2/kW
OUTAGE_LENGTH = 24  # hrs

# Calculated Data:
PRODUCTION, ANNUAL_PRODUCTION = si.read_pvwatts("input/pvwatts_hourly.csv")  # kWh/yr
USAGE, ANNUAL_USAGE = si.read_usage("input/usage.csv")

USAGE_CONSTRAINTS = si.generate_constraints(
    USAGE,
    OUTAGE_LENGTH,
)
PRODUCTION_CONSTRAINTS = si.generate_constraints(
    PRODUCTION,
    OUTAGE_LENGTH,
)
# ---------------- END DATA ---------------- #


def print_progress_bar(
    iteration,
    total,
    prefix="",
    suffix="",
    decimals=1,
    length=100,
    fill="█",
    print_end="\r",
):
    """
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        length      - Optional  : character length of bar (Int)
        fill        - Optional  : bar fill character (Str)
        printEnd    - Optional  : end character (e.g. "\r", "\r\n") (Str)
    """
    # Credit: https://stackoverflow.com/a/34325723 with minor adaptations.
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filled_length = int(length * iteration // total)
    block = fill * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{block}| {percent}% {suffix}", end=print_end)
    if iteration == total:
        print()


def solve_problem(production, usage):
    """Create a model based on inputs, and solve for the optimal installation."""

    # Initialize the solver
    solver = pywraplp.Solver.CreateSolver("SCIP")

    infinity = solver.infinity()

    # Initialize variables:
    x_A = solver.NumVar(0, infinity, "solar_capacity")
    x_B = solver.NumVar(0, infinity, "battery_capacity")

    # Temporal variables
    B_list = [solver.NumVar(0, infinity, f"charge_{i}") for i in range(len(usage))]
    d_in = [solver.NumVar(0, infinity, f"delta_in_{i}") for i in range(len(usage))]
    d_out = [solver.NumVar(0, infinity, f"delta_out_{i}") for i in range(len(usage))]
    d_c = [solver.IntVar(0, 1, f"charging_{i}") for i in range(len(usage))]
    d_dc = [solver.IntVar(0, 1, f"discharging_{i}") for i in range(len(usage))]

    # Initialize constraints:
    solver.Add(ANNUAL_PRODUCTION * x_A <= ANNUAL_USAGE)
    solver.Add(AREA_USAGE * x_A <= ROOF_AREA)

    # Temporal constraints
    for i, _ in enumerate(production):
        solver.Add(d_in[i] <= production[i] * x_A - usage[i] * d_c[i])

        solver.Add(usage[i] - production[i] * x_A <= d_out[i])

        solver.Add(x_B * MIN_CHARGE <= B_list[i])

        solver.Add(B_list[i] <= x_B)

        solver.Add(d_out[i] <= B_list[i - 1])
        solver.Add(d_out[i] <= BIG_M * d_dc[i])

        solver.Add(d_in[i] <= x_B - B_list[i - 1])
        solver.Add(d_in[i] <= BIG_M * d_c[i])

        solver.Add(d_c[i] + d_dc[i] <= 1)

        if i != 0:
            solver.Add(B_list[i] <= B_list[i - 1] + d_in[i] - d_out[i])
        else:
            solver.Add(B_list[i] <= x_B)

    # Define the objective function:
    solver.Maximize(
        (-TAX_MODIFIER * ARRAY_COST + ENERGY_COST * ANNUAL_PRODUCTION * SYSTEM_LIFESPAN)
        * x_A
        - BATTERY_COST * x_B
    )

    # Solve the model
    status = solver.Solve()

    # Collect and pack solution values into a dictionary
    if status == pywraplp.Solver.OPTIMAL:
        solution = {}
        solution["obj"] = solver.Objective().Value()
        solution["x_A"] = x_A.solution_value()
        solution["x_B"] = x_B.solution_value()
        solution["B_list"] = [i.solution_value() for i in B_list]
        solution["d_in"] = [i.solution_value() for i in d_in]
        solution["d_out"] = [i.solution_value() for i in d_out]
        solution["d_c"] = [i.solution_value() for i in d_c]
        solution["d_dc"] = [i.solution_value() for i in d_dc]
        return solution

    # If there is no solution:
    print("The problem does not have an optimal solution.")
    return None


def plot_charge(index, solution, scenario):
    """Plot a chart detailing charge level over the outage period."""
    plt.style.use("ggplot")

    _, ax = plt.subplots()
    data = solution["B_list"][index]
    colors = []
    for i in range(len(solution["d_dc"][index])):
        if solution["d_dc"][index][i]:
            colors.append("gray")
        elif solution["d_c"][index][i]:
            colors.append("black")
        else:
            colors.append("white")

    ax.bar(range(OUTAGE_LENGTH), data, color=colors)

    ax.set_ylabel("Charge (kWh)")
    ax.set_xlabel("Hour")
    ax.set(xlim=(-1, OUTAGE_LENGTH), xticks=np.arange(0, OUTAGE_LENGTH))

    ax.set_title(scenario)
    plt.suptitle(f"Charge status during {OUTAGE_LENGTH}-hour outage")

    plt.savefig(f"img/fig_c_{scenario}")

    ax.clear()
    plt.clf()


def plot_usage_production(index, solution, scenario):
    """Plot a chart detailing energy usage and production over the outage period."""
    plt.style.use("ggplot")

    x = range(OUTAGE_LENGTH)

    plt.plot(x, USAGE_CONSTRAINTS[index], "black", label="Usage")

    total_production = [
        solution["x_A"][index] * i for i in PRODUCTION_CONSTRAINTS[index]
    ]
    plt.plot(x, total_production, "gray", label="Production")

    plt.xlabel("Hour")
    plt.ylabel("Energy (kWh)")

    plt.suptitle(f"Usage versus production during {OUTAGE_LENGTH}-hour outage")
    plt.title(scenario)

    plt.legend()
    plt.xticks(np.arange(min(x), max(x) + 1, 1.0))

    plt.savefig(f"img/fig_up_{scenario}")

    plt.plot().clear()
    plt.clf()


def plot_payback_period(index, solution, scenario):
    """Plot a chart detailing the years until the system pays for itself."""
    plt.plot().clear()
    plt.style.use("ggplot")

    x = range(SYSTEM_LIFESPAN + 1)
    arr_cost = solution["x_A"][index] * ARRAY_COST
    batt_cost = solution["x_B"][index] * BATTERY_COST
    total_cost = TAX_MODIFIER * arr_cost + batt_cost
    year_prod = solution["x_A"][index] * ANNUAL_PRODUCTION * ENERGY_COST

    plt.plot(x, [0 for _ in x], "gray")

    plt.plot(x, [i * year_prod - total_cost for i in x], "black", label="Net Cost")

    plt.xlabel("Year")
    plt.ylabel("Savings")

    plt.text(0.5, -1000, f"Break-even year: {(total_cost / year_prod):.0f}")

    plt.suptitle(f"Net Savings over {SYSTEM_LIFESPAN}-year Span")
    plt.title(scenario)

    plt.legend()
    plt.xticks(np.arange(min(x), max(x) + 1, 1.0))

    plt.tight_layout()

    plt.savefig(f"img/fig_pp_{scenario}")

    plt.plot().clear()
    plt.clf()

    # plt.show()


def report(index, solution, scenario):
    """Formats the output and generates several charts."""
    print(f"Scenario: {scenario}")
    dummy = solution["obj"][index]
    print(f"Objective function value: ${dummy:.2f}")

    dummy = solution["x_A"][index]
    print(f"Array Capacity: {dummy:.3f} kW")

    arr_cost = solution["x_A"][index] * ARRAY_COST
    print(f"Cost of array: ${arr_cost:.2f}")

    dummy = solution["x_B"][index]
    print(f"Battery Capacity: {dummy:.3f} kWh")

    batt_cost = solution["x_B"][index] * BATTERY_COST
    print(f"Cost of batteries: ${batt_cost:.2f}")

    dummy = TAX_MODIFIER * arr_cost + batt_cost
    print(f"Combined upfront cost (with tax credit): ${dummy:.2f}")

    dummy = solution["x_A"][index] * ENERGY_COST * ANNUAL_PRODUCTION * SYSTEM_LIFESPAN
    print(f"Energy cost offset: ${dummy:.2f}")

    print()

    plot_charge(index, solution, scenario)
    plot_usage_production(index, solution, scenario)
    plot_payback_period(index, solution, scenario)


def main():
    """The main entrypoint for the program."""
    solution = {
        "obj": [],
        "x_A": [],
        "x_B": [],
        "B_list": [],
        "d_in": [],
        "d_out": [],
        "d_c": [],
        "d_dc": [],
    }
    goal = len(USAGE_CONSTRAINTS)
    if not exists("solutions.json"):
        start_time = time.time()
        # Solve a problem for each 24-hour period in the year.
        for i in range(goal):
            result = solve_problem(PRODUCTION_CONSTRAINTS[i], USAGE_CONSTRAINTS[i])
            for j in result:
                solution[j].append(result[j])
            print_progress_bar(
                i + 1,
                goal,
                suffix=f"Problem {i+1} | Time elapsed: {time.time() - start_time:.2f}s",
            )
        print(f"{goal} problems solved in {time.time() - start_time:.2f} seconds")
        json_out = json.dumps(solution)
        with open("solutions.json", "w", encoding="utf-8") as f:
            f.write(json_out)
    else:
        with open("solutions.json", "r", encoding="utf-8") as f:
            solution = json.load(f)
            print("Loaded solutions from solutions.json.")
            print("Delete the file to recalculate.")
    max_i = np.argmax(solution["x_B"])
    min_i = np.argmin(solution["x_B"])
    median_i = np.argsort(solution["x_B"])[len(solution["x_B"]) // 2]

    report(max_i, solution, "worst_case")
    report(min_i, solution, "best_case")
    report(median_i, solution, "median_case")


if __name__ == "__main__":
    main()
