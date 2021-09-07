import qiskit
from qiskit.ignis.mitigation.measurement import (complete_meas_cal,
                                                 CompleteMeasFitter,
                                                 MeasurementFilter)
from qiskit.providers.aer import noise
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
#
results = job.result()

# Results without mitigation
raw_counts = results.get_counts()
print("Results without mitigation:", raw_counts)

# Create a measurement filter from the calibration matrix
meas_filter = meas_fitter.filter
# Apply the filter to the raw counts to mitigate
# the measurement errors
mitigated_counts = meas_filter.apply(raw_counts)
print("Results with mitigation:", {l:int(mitigated_counts[l]) for l in mitigated_counts})
