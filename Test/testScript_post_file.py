import qiskit
from qiskit.ignis.mitigation.measurement import (complete_meas_cal,
                                                 CompleteMeasFitter,
                                                 MeasurementFilter)
from qiskit.providers.aer import noise
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
def post(noise_model, read_err, qr, meas_cals, state_labels, backend, job, cal_results, meas_fitter, cr, ghz, results, ): 

    solve(results)
    # Results without mitigation
    raw_counts = results.get_counts()
    print("Results without mitigation:", raw_counts)
    return [raw_counts]
