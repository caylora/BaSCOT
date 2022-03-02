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
    # Create the solver
    solver = pywraplp.Solver.CreateSolver("SCIP")
    x_b = solver.NumVar(0, solver.infinity(), "x_b")
    charging = solver.IntVar(0, 1, "charging")
    discharging = solver.IntVar(0, 1, "discharging")
    energy_stored = solver.NumVar(0, solver.infinity(), "energy_stored")
    energy_stored_old = solver.NumVar(0, solver.infinity(), "energy_stored_old")
    energy_in = solver.NumVar(0, solver.infinity(), "energy_in")
    energy_out = solver.NumVar(0, solver.infinity(), "energy_out")

    # Define constraints

    solver.Add(energy_out <= energy_stored_old)
    solver.Add(energy_stored <= x_b)
    solver.Add(energy_out <= energy_stored * discharging)
    solver.Add(energy_in <= (x_b - energy_stored) * charging)
    solver.Add(discharging + charging <= 1)

    solver.Add(energy_stored=energy_stored_old + energy_in - energy_out)

    # Define the variables:
    x_list = {}
    for count, value in enumerate(data["variables"]):
        if value[1] == "int":
            x_list[count] = solver.IntVar(0, solver.infinity(), value[0])
        elif value[1] == "bin":
            x_list[count] = solver.IntVar(0, 1, value[0])
        else:
            x_list[count] = solver.NumVar(0, solver.infinity(), value[0])

    # Initialize storage constraint
    solver.Add(energy_stored=energy_stored_old + energy_in - energy_out)
    
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
