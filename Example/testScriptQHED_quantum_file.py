import qiskit
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import style
from qiskit.visualization import *
from qiskit.tools.monitor import job_monitor
from qiskit.compiler import transpile
from qiskit import IBMQ, QuantumCircuit, execute, display
def quantum(image, image_small, data_qb, anc_qb, total_qb, NoLoopFound, ): 

    IBMQ.load_account()

    # Get the provider and backend
    provider = IBMQ.get_provider(hub='ibm-q', group='open')
    backend = provider.get_backend('ibmq_santiago')

    # Create the circuit for horizontal scan
    qc_small_h = QuantumCircuit(total_qb)
    qc_small_h.x(1)
    qc_small_h.h(0)

    # Decrement gate - START
    qc_small_h.x(0)
    qc_small_h.cx(0, 1)
    qc_small_h.ccx(0, 1, 2)
    # Decrement gate - END

    qc_small_h.h(0)
    qc_small_h.measure_all()
    display(qc_small_h.draw('mpl'))

    # Create the circuit for vertical scan
    qc_small_v = QuantumCircuit(total_qb)
    qc_small_v.x(2)
    qc_small_v.h(0)

    # Decrement gate - START
    qc_small_v.x(0)
    qc_small_v.cx(0, 1)
    qc_small_v.ccx(0, 1, 2)
    # Decrement gate - END

    qc_small_v.h(0)
    qc_small_v.measure_all()
    display(qc_small_v.draw('mpl'))

    # Combine both circuits into a single list
    circ_list = [qc_small_h, qc_small_v]

    # Transpile the circuits for optimized execution on the backend
    qc_small_h_t = transpile(qc_small_h, backend=backend, optimization_level=3)
    qc_small_v_t = transpile(qc_small_v, backend=backend, optimization_level=3)

    # Combining both circuits into a list
    circ_list_t = [qc_small_h_t, qc_small_v_t]

    # Executing the circuits on the backend
    job = execute(circ_list_t, backend=backend, shots=8192)
    job_monitor(job)


    # Getting the resultant probability distribution after measurement
    result = job.result()
    counts_h = result.get_counts(qc_small_h)
    counts_v = result.get_counts(qc_small_v)

    print('Counts for Horizontal scan:')
    display(plot_histogram(counts_h))

    print('\n\nCounts for Vertical scan:')
    display(plot_histogram(counts_v))
    return [provider, backend, qc_small_h, qc_small_v, circ_list, qc_small_h_t, qc_small_v_t, circ_list_t, job, result, counts_h, counts_v, image, image_small, data_qb, anc_qb, total_qb]
