# ref: https://github.com/Qiskit/qiskit-ignis
# Import Qiskit classes
import qiskit
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
from qiskit.providers.aer import noise
 # import AER noise model

# Measurement error mitigation functions
from qiskit.ignis.mitigation.measurement import (complete_meas_cal,
                                                 CompleteMeasFitter,
                                                 MeasurementFilter)

# Generate a noise model for the qubits
#
