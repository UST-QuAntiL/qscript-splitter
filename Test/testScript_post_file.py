import qiskit
from qiskit.ignis.mitigation.measurement import (complete_meas_cal,
                                                 CompleteMeasFitter,
                                                 MeasurementFilter)
from qiskit.providers.aer import noise
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
def post(): 

    solve(results)
    # Results without mitigation
    raw_counts = results.get_counts()
    print("Results without mitigation:", raw_counts)
    return [raw_counts]
