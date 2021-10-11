import qiskit
from qiskit.ignis.mitigation.measurement import (complete_meas_cal,
                                                 CompleteMeasFitter,
                                                 MeasurementFilter)
from qiskit.providers.aer import noise
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
def pre(): 


    # Calculate parameters
    number_of_independent_results = 5
    qubits = 5
    classical_bits = 3

    return [number_of_independent_results, qubits, classical_bits]
