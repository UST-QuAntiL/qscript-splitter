from typing import List, Callable, Dict
import math

from qiskit import QuantumCircuit
from qiskit.circuit import Parameter
from qiskit.opflow import I, X, Y, Z, StateFn, PauliExpectation, OperatorBase

import numpy as np


params = [Parameter(str(i)) for i in range(4)]
qc = QuantumCircuit(2)

qc.rx(params[0], 0)
qc.rx(params[1], 1)
qc.cnot(0, 1)
qc.rx(params[2], 0)
qc.rx(params[3], 1)

observable = StateFn(Z ^ Z).adjoint()

target = 0.7

values = np.array([0.8, 0.8, 0.4, 0.5])
values = np.random.uniform(size=4)
learning_rate = 0.1
# print(sqrt_error(values))

for i in range(100):
	# Calculate Gradient
	r = 0.5
	s = math.pi / (4.0 * r)
	grad = np.zeros_like(values)
	for i in range(len(params)):
		values_plus = values.copy()
		values_plus[i] += s
		exp_plus = calc_expectation(qc, observable, params, values_plus)

		values_minus = values.copy()
		values_minus[i] -= s
		exp_minus = calc_expectation(qc, observable, params, values_minus)

		partial_derivative = r * (exp_plus - exp_minus)
		grad[i] = partial_derivative

	# Calculate expectation
	qc_op = StateFn(qc.bind_parameters({k: v for k, v in zip(params, values)}))
	out = PauliExpectation().convert(observable @ qc_op).eval().real

	grad *= 2 * out - 2 * target  # derivative of sqrt error

	values -= learning_rate * grad

	# print(sqrt_error(qc, observable, params, values, target))
	print(calc_expectation(qc, observable, params, values))
	# print("{:.2f}, {:.2f}, {:.2f}, {:.2f}: {:.2f}".format(grad[0], grad[1], grad[2], grad[3], sqrt_error(values)))

print(values)