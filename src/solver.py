"""Module for solving models."""
from ortools.linear_solver import pywraplp


def solve_model(data):
    """Solve a model based on the input data."""

    # Create the solver
    solver = pywraplp.Solver.CreateSolver("GLOP")

    # Define the variables:
    x_list = {}
    for count, value in enumerate(data["variables"]):
        x_list[count] = solver.NumVar(0, solver.infinity(), value)

    # Define the constraints:
    for i in data["constraints"]:
        # Pull info from constraint at index i:
        # Construct the naked expression using coefficients
        constraint_expr = [i[0][j] * x_list[j] for j in range(data["vars"])]
        # Construct the full expression using the bound
        solver.Add(sum(constraint_expr) <= i[1])

    # Define the objective function:
    obj_expr = [data["objective"][j] * x_list[j] for j in range(data["vars"])]
    solver.Maximize(solver.Sum(obj_expr))

    print("Solving a problem with:", end="\t")
    print(f"{solver.NumVariables()} variables", end=", ")
    print(f"{solver.NumConstraints()} constraints")
    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        solution = {}
        solution["obj_value"] = solver.Objective().Value()
        for i in range(data["vars"]):
            solution[x_list[i].name()] = x_list[i].solution_value()
        return solution
    print("The problem does not have an optimal solution.")
    return None


def model_battery_state(data):
    """Model battery state over period of production and consumption."""
    solver = pywraplp.Solver.CreateSolver("SCIP")
    battery_capacity = solver.NumVar(0, solver.infinity(), "battery_capacity")
    charging = solver.IntVar(0, 1, "charging")
    discharging = solver.IntVar(0, 1, "discharging")
    energy_stored = solver.NumVar(0, solver.infinity(), "energy_stored")

    # Define constraints
    solver.Add(energy_out <= energy_stored_-1)
    solver.Add(min_charge * batt_size <= energy_stored)
    solver.Add(energy_stored <= max_charge)
    solver.Add(energy_out <= max_charge * discharging)
    solver.Add(energy_in <= max_charge * charging)
    solver.Add(discharging + charging <= 1)

    solver.Maximize(-)


    return None
