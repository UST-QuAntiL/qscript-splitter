import qiskit
from qiskit.ignis.mitigation.measurement import (complete_meas_cal,
                                                 CompleteMeasFitter,
                                                 MeasurementFilter)
from qiskit.providers.aer import noise
from qiskit import QuantumRegister, QuantumCircuit, ClassicalRegister
def quantum(number_of_independent_results, qubits, classical_bits, i, ): 

    for _loop_dummy in range(1):
        # Generate a noise model for the qubits
        noise_model = noise.NoiseModel()
        for qi in range(5):
            read_err = noise.errors.readout_error.ReadoutError([[0.75, 0.25], [0.1, 0.9]])
            noise_model.add_readout_error(read_err, [qi])
    
        # Generate the measurement calibration circuits
        # for running measurement error mitigation
        qr = QuantumRegister(qubits)
        meas_cals, state_labels = complete_meas_cal(qubit_list=[2, 3, 4], qr=qr)
    
        # Execute the calibration circuits
        backend = qiskit.Aer.get_backend('qasm_simulator')
        job = qiskit.execute(meas_cals, backend=backend, shots=1000, noise_model=noise_model)
        cal_results = job.result()
    
        # Make a calibration matrix
        meas_fitter = CompleteMeasFitter(cal_results, state_labels)
    
        # Make a 3Q GHZ state
        cr = ClassicalRegister(classical_bits)
        ghz = QuantumCircuit(qr, cr)
        ghz.h(qr[2])
        ghz.cx(qr[2], qr[3])
        ghz.cx(qr[3], qr[4])
        ghz.measure(qr[2], cr[0])
        ghz.measure(qr[3], cr[1])
        ghz.measure(qr[4], cr[2])
    
        # Execute the GHZ circuit (with the same noise model)
        job = qiskit.execute(ghz, backend=backend, shots=1000, noise_model=noise_model)
        results = job.result()
    
    
    # Results without mitigation
    return [noise_model, read_err, qr, meas_cals,  state_labels, backend, job, cal_results, meas_fitter, cr, ghz, results, number_of_independent_results, qubits, classical_bits]
