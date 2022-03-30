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
ARRAY_COST = 2989  # $/kW
TAX_MOD = 0.74
BATTERY_COST = 345  # $/kWh
ENERGY_COST = 0.134  # current $/kWh
SPAN = 25  # yrs
ROOF_AREA = 30  # m^2
AREA_USAGE = 5.181  # m^2/kW
OUTAGE_LENGTH = 24  # hrs

# Calculated Data:
PROD_DATA, TOTAL_PROD = si.read_pvwatts("input/pvwatts_hourly.csv")  # kWh/yr
USAGE_DATA, TOTAL_USAGE = si.read_usage("input/usage.csv")

USAGE_VALUES = si.generate_constraints(
    USAGE_DATA,
    OUTAGE_LENGTH,
)
PROD_VALUES = si.generate_constraints(
    PROD_DATA,
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
    bar = fill * filled_length + "-" * (length - filled_length)
    print(f"\r{prefix} |{bar}| {percent}% {suffix}", end=print_end)
    if iteration == total:
        print()


def solve_problem(production, usage):
    solver = pywraplp.Solver.CreateSolver("SCIP")
    infinity = solver.infinity()

    # Variables:
    x_A = solver.NumVar(0, infinity, "solar_capacity")
    x_B = solver.NumVar(0, infinity, "battery_capacity")
    B_list = [solver.NumVar(0, infinity, "charge_%i" % i) for i in range(len(usage))]
    d_in = [solver.NumVar(0, infinity, "delta_in_%i" % i) for i in range(len(usage))]
    d_out = [solver.NumVar(0, infinity, "delta_out_%i" % i) for i in range(len(usage))]
    d_c = [solver.IntVar(0, 1, "charging_%i" % i) for i in range(len(usage))]
    d_dc = [solver.IntVar(0, 1, "discharging_%i" % i) for i in range(len(usage))]

    # Constraints:
    solver.Add(TOTAL_PROD * x_A <= TOTAL_USAGE)
    solver.Add(AREA_USAGE * x_A <= ROOF_AREA)

    for i in range(len(production)):
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
        (-TAX_MOD * ARRAY_COST + ENERGY_COST * TOTAL_PROD * SPAN) * x_A
        - BATTERY_COST * x_B
    )
    # print("Solving a problem with:", end="\t")
    # print(f"{solver.NumVariables()} variables", end=", ")
    # print(f"{solver.NumConstraints()} constraints")
    status = solver.Solve()

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
    print("The problem does not have an optimal solution.")
    return None


def plot_charge(index, solution, s):
    plt.style.use("ggplot")

    fig, ax = plt.subplots()
    data = solution["B_list"][index]
    c = []
    for i in range(len(solution["d_dc"][index])):
        if solution["d_dc"][index][i]:
            c.append("gray")
        elif solution["d_c"][index][i]:
            c.append("black")
        else:
            c.append("white")

    ax.bar(range(OUTAGE_LENGTH), data, color=c)

    ax.set_ylabel("Charge (kWh)")
    ax.set_xlabel("Hour")
    ax.set(xlim=(-1, OUTAGE_LENGTH), xticks=np.arange(0, OUTAGE_LENGTH))

    ax.set_title(s)
    plt.suptitle("Charge status during %s-hour outage" % OUTAGE_LENGTH)

    plt.savefig("img/fig_c_%s" % s)

    ax.clear()
    plt.clf()


def plot_usage_production(index, solution, s):
    plt.style.use("ggplot")

    x = range(OUTAGE_LENGTH)

    plt.plot(x, USAGE_VALUES[index], "black", label="Usage")

    total_production = [solution["x_A"][index] * i for i in PROD_VALUES[index]]
    plt.plot(x, total_production, "gray", label="Production")

    plt.xlabel("Hour")
    plt.ylabel("Energy (kWh)")

    plt.suptitle("Usage versus production during %s-hour outage" % OUTAGE_LENGTH)
    plt.title(s)

    plt.legend()
    plt.xticks(np.arange(min(x), max(x) + 1, 1.0))

    plt.savefig("img/fig_up_%s" % s)

    plt.plot().clear()
    plt.clf()


def plot_payback_period(index, solution, s):
    plt.plot().clear()
    plt.style.use("ggplot")

    x = range(SPAN + 1)
    arr_cost = solution["x_A"][index] * ARRAY_COST
    batt_cost = solution["x_B"][index] * BATTERY_COST
    total_cost = TAX_MOD * arr_cost + batt_cost
    year_prod = solution["x_A"][index] * TOTAL_PROD * ENERGY_COST

    plt.plot(x, [0 for _ in x], "gray")

    plt.plot(x, [i * year_prod - total_cost for i in x], "black", label="Net Cost")

    plt.xlabel("Year")
    plt.ylabel("Savings")

    plt.text(0.5, -1000, "Break-even year: %.0f" % (total_cost / year_prod))

    plt.suptitle("Net Savings over %s-year Span" % SPAN)
    plt.title(s)

    plt.legend()
    plt.xticks(np.arange(min(x), max(x) + 1, 1.0))

    plt.tight_layout()

    plt.savefig("img/fig_pp_%s" % s)

    plt.plot().clear()
    plt.clf()

    # plt.show()

    return None


def report(index, solution, s):
    print("Scenario: %s" % s)
    print("Objective function value: $%.2f" % solution["obj"][index])

    print("Array Capacity: %.3f" % solution["x_A"][index], "kW")

    arr_cost = solution["x_A"][index] * ARRAY_COST
    print("Cost of array: $%.2f" % arr_cost)

    print("Battery Capacity: %.3f" % solution["x_B"][index], "kWh")

    batt_cost = solution["x_B"][index] * BATTERY_COST
    print("Cost of batteries: $%.2f" % batt_cost)

    print(
        "Combined upfront cost (with tax credit): $%.2f"
        % (TAX_MOD * arr_cost + batt_cost)
    )
    print(
        "Energy cost offset: $%.2f"
        % (solution["x_A"][index] * ENERGY_COST * TOTAL_PROD * SPAN)
    )

    print()

    plot_charge(index, solution, s)
    plot_usage_production(index, solution, s)
    plot_payback_period(index, solution, s)


def main():
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
    goal = len(USAGE_VALUES)
    if not exists("solutions.json"):
        start_time = time.time()
        for i in range(goal):
            result = solve_problem(PROD_VALUES[i], USAGE_VALUES[i])
            for j in result:
                solution[j].append(result[j])
            print_progress_bar(
                i + 1,
                goal,
                suffix="Problem %i | Time elapsed: %.2fs"
                % (i + 1, time.time() - start_time),
            )
        print("%s problems solved in %.2f seconds" % (goal, time.time() - start_time))
        json_out = json.dumps(solution)
        with open("solutions.json", "w") as f:
            f.write(json_out)
    else:
        with open("solutions.json", "r") as f:
            solution = json.load(f)
            print(
                "Loaded solutions from solutions.json. Delete the file and rerun if you make changes to the data or equations to recalculate."
            )
    max_i = np.argmax(solution["x_B"])
    min_i = np.argmin(solution["x_B"])
    median_i = np.argsort(solution["x_B"])[len(solution["x_B"]) // 2]

    report(max_i, solution, "worst_case")
    report(min_i, solution, "best_case")
    report(median_i, solution, "median_case")


if __name__ == "__main__":
    main()
