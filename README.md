# BaSCOT: Battery and Solar Capacity Optimization Tool

##### Date: 15 December 2021

##### Alton Caylor

##### email: caylora@allegheny.edu

---

![logo](img/BaSCOT_logo.png)

BaSCOT is an optimization tool that uses the OR-Tools library to solve linear optimization problems, determining the optimal capacity of solar panels and battery storage to maximize savings and improving energy resiliency in the face of grid outages.

## Installing / Getting started

Ensure python 3.9 or greater is installed, then run the following commands to execute the program.

```cmd
pip install or-tools
pip install numpy

python src/__main__.py
```

Sample output:

```sample
Total annual energy usage: 5533.79kWh

Objective value = $10889.95 saved over 25 year span.
Solar Capacity = 4.542 kW
Battery Capacity = 18.549 kWh

Cost of solar modules = $13170.54
Cost of batteries = $6399.41
```

## Features

TODO: Add description

## Background

## Links

* [Repository](https://github.com/caylora/BaSCOT)
* [REopt Lite by NREL](https://github.com/NREL/REoptLite)
