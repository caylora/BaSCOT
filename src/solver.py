"""Module for solving models."""
import sys

from ortools.linear_solver import pywraplp


def solve_model(data):
    """Solve a model based on the input data."""

    # Create the solver
    solver = pywraplp.Solver.CreateSolver("GLOP")

    # Define the variables:
    x_list = {}
    for count, value in enumerate(data["variable_name"]):
        x_list[count] = solver.NumVar(0, solver.infinity(), value)
    # print(f"Number of variables = {solver.NumVariables()}")

    # Define the constraints:
    for i in range(data["num_constraints"]):
        constraint_expr = [
            data["constraint_coeffs"][i][j] * x_list[j] for j in range(data["num_vars"])
        ]
        if data["constraint_signs"][i] == "<=":
            solver.Add(sum(constraint_expr) <= data["bounds"][i])
        elif data["constraint_signs"][i] == ">=":
            solver.Add(sum(constraint_expr) >= data["bounds"][i])
        else:
            print("Sign missing for constraint.")
            sys.exit()
    # print("Number of constraints =", solver.NumConstraints())

    # Define the objective function:
    obj_expr = [data["obj_coeffs"][j] * x_list[j] for j in range(data["num_vars"])]
    solver.Maximize(solver.Sum(obj_expr))

    status = solver.Solve()

    if status == pywraplp.Solver.OPTIMAL:
        solution = {}
        solution["obj_value"] = solver.Objective().Value()
        for i in range(data["num_vars"]):
            solution[x_list[i].name()] = x_list[i].solution_value()
        return solution
    print("The problem does not have an optimal solution.")
    return None
