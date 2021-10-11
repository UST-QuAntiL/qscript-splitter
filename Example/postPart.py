import qiskit
from qiskit.ignis.mitigation.measurement import (complete_meas_cal,
                                                 CompleteMeasFitter,
                                                 MeasurementFilter)
from qiskit.providers.aer import noise
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
def post(noise_model, read_err, qr, meas_cals, state_labels, backend, job, cal_results, meas_fitter, cr, ghz, results, number_of_independent_results, qubits, classical_bits, ): 

    counts = results.get_counts()
    # interpret the results or do some further processing
    # ...
    print("Results: ", counts)
    return [counts]
