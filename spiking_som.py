
from brian2 import *

from pyqtgraph.Qt import QtGui, QtCore
import numpy as np
import pyqtgraph as pg

import matplotlib.pyplot as plt

from dataset import ArtificialDataSet


class ReceptiveField:
    # Parameter that used in standard deviation definition
    gamma = 1.5

    def __init__(self, bank_size=10, I_min=0.0, I_max=1.0):
        self.bank_size = bank_size
        self.field_mu = np.array([(I_min + ((2 * i - 2) / 2) * ((I_max - I_min) / (bank_size - 1)))
                                  for i in range(1, bank_size + 1)])
        self.field_sigma = (1.0 / self.gamma) * (I_max - I_min)

    def float_to_membrane_potential(self, input_vector):
        try:
            input_vector = input_vector.reshape((input_vector.shape[0], 1))
        except Exception as exc:
            print("Exception: {0}\nObject shape: {1}".format(repr(exc), input_vector.shape))
            exit(1)

        temp = np.exp(-((input_vector - self.field_mu) ** 2) / (2 * self.field_sigma * self.field_sigma)) / \
               (np.sqrt(2 * np.pi) * self.field_sigma)
        temp += np.exp(-((input_vector - 1 - self.field_mu) ** 2) / (2 * self.field_sigma * self.field_sigma)) / \
                (np.sqrt(2 * np.pi) * self.field_sigma)
        temp += np.exp(-((input_vector + 1 - self.field_mu) ** 2) / (2 * self.field_sigma * self.field_sigma)) / \
                (np.sqrt(2 * np.pi) * self.field_sigma)

        return temp


if __name__ == "__main__":

    prefs.codegen.target = 'numpy'

    np.random.seed(1)
    seed(1)
    np.set_printoptions(suppress=True)

    bank_size = 10
    diff_method = 'euler'

    # inputs = np.random.rand(3)
    # inputs = np.array([0.332, 0.167, 0.946])
    # inputs = np.array([0.013, 0.3401, 0.2196])
    # inputs = np.array([0.829, 0.7452, 0.6728])
    # print(inputs)
    # N = inputs.shape[0] * bank_size
    N = 20
    rf = ReceptiveField(bank_size=bank_size, I_min=0.05, I_max=0.95)
    # potential_input = rf.float_to_membrane_potential(inputs)
    # potential_input = potential_input.flatten()

    # TABLE 1 
    # (A) Neuronal parameters, used in (1) and (4)
    time_step = 0.01;
    tau_m = 10.0 * ms;
    tau_m_inh = 5 * ms;
    tau_m_som = 3 * ms
    theta_reset_u = -0.5;
    theta_reset_inh = -0.0;
    theta_reset_som = 0.0
    theta_u = 0.5;
    theta_u_inh = 0.01;
    theta_som = 0.8
    # (B) Synaptic parameters, used in (2) and (3) for different synapse types
    # temporal layer to som layer (u to v)
    tau_r_afferent = 0.2 * ms;
    tau_f_afferent = 1.0 * ms
    # temporal layer (u to inh exc, u to inh inh, inh to u)
    tau_r_exc = 0.4 * ms;
    tau_f_exc = 2.0 * ms;
    tau_r_inh = 0.2 * ms;
    tau_f_inh = 1.0 * ms
    tau_r_inh2u = 1.0 * ms;
    tau_f_inh2u = 5.0 * ms
    # som layer
    tau_r_lateral = 0.1 * ms;
    tau_f_lateral = 0.5 * ms
    # (C) Maximum magnitudes of synaptic connection strength
    w_syn_temporal_to_som_max = 2.2;
    w_syn_u2inh_exc_max = 1.0;
    w_syn_u2inh_inh_max = 1.0;
    w_syn_inh2u_max = 100.0
    w_syn_som_to_som_max = 1.0
    # (D) Neighbourhood parameters, used in (6) and (7), for layer v (som)
    a = 3.0;
    b = 3.0;
    X = 3.0;
    X_ = 3.0
    # (E) Learning parameter, used in (5)
    # A_plus - Max synaptic strength, A_minus - max synaptic weakness; tau_plus, tau_minus - time constant of STDP
    A_plus = 0.0016;
    A_minus = 0.0055;
    tau_plus = 11;
    tau_minus = 10

    # used in (7)
    T = 10.0;
    power_n = 2.0
    # used in (6)
    pi = np.pi
    # size of the self-organizing map
    map_size = 10


    temporal_layer_neuron_equ = '''
        dtime/dt = 1 / ms : 1
        
        # inhibition connection to u layer
        
        ds_inh2u/dt = (-s_inh2u)/tau_r_inh2u: 1
        dw_inh2u/dt = (s_inh2u - w_inh2u)/tau_f_inh2u: 1

        # membrane potential of u layer
        
        dv/dt = (-v + I_ext - w_inh2u) / tau_m: 1
        I_ext : 1
    '''
    inhibition_neuron_equ = '''
            dtime/dt = 1 / ms : 1

            # inhibition connection
            # s_inh - internal variable
            # w_inh - output potential

            ds_inh/dt = (-s_inh)/tau_r_inh: 1
            dw_inh/dt = (s_inh - w_inh)/tau_f_inh: 1

            # excitation connection
            # s_exc - internal variable
            # w_exc - output potential
            ds_exc/dt = (-s_exc)/tau_r_exc: 1
            dw_exc/dt = (s_exc - w_exc)/tau_f_exc: 1

            # diff equation membrane potential of inhibition neuron
            dv/dt = (-v + w_exc - w_inh) / tau_m_inh: 1
        '''
    som_layer_neuron_equ = '''
                dglobal_time/dt = 1 / ms : 1
                dtime/dt = 1 / ms : 1

                # Afferent connection (from temporal layer to som layer)

                ds_afferent/dt = (-s_afferent)/tau_r_afferent: 1
                dw_afferent/dt = (s_afferent - w_afferent)/tau_f_afferent: 1 

                # lateral connection

                ds_lateral/dt = (-s_lateral)/tau_r_lateral: 1
                dw_lateral/dt = (s_lateral - w_lateral)/tau_f_lateral: 1

                # membrane potential of u layer

                dv/dt = (-v + w_lateral + w_afferent) / tau_m_som: 1
            '''

    temporal_layer = NeuronGroup(N, temporal_layer_neuron_equ, threshold='v>theta_u', method=diff_method,
                                 reset='''v = theta_reset_u; time = 0''')
    # temporal_layer.I_ext = potential_input

    # inhibition neuron
    inhibition_neuron = NeuronGroup(1, inhibition_neuron_equ, threshold='v>theta_u_inh', method=diff_method,
                                    reset='''v = theta_reset_inh; time = 0''')
    # self-organizing layer
    som_layer = NeuronGroup(map_size * map_size, som_layer_neuron_equ, threshold='v>theta_som', method=diff_method,
                            reset='''v = theta_reset_som; time = 0''')

    # v to inh neuron, excitation connection
    u2inh_excitation = Synapses(temporal_layer, target=inhibition_neuron, method=diff_method,
                                on_pre='''
                                s_exc += w_syn
                                A_pre = (- w_syn) * A_minus * (1 - 1/tau_minus) ** time_post
                                w_syn = clip(w_syn + plasticity * A_pre, 0, w_syn_u2inh_exc_max) 
                                ''',
                                on_post='''
                                A_post = exp(-w_syn) * A_plus * (1 - 1/tau_plus) ** time_pre
                                w_syn = clip(w_syn + plasticity * A_post, 0, w_syn_u2inh_exc_max)
                                ''',
                                model='''
                                w_syn : 1 # synaptic weight / synapse efficacy
                                plasticity : boolean (shared)
                                ''')
    u2inh_excitation.connect(i=np.arange(N), j=0)
    u2inh_excitation.w_syn = 'rand() * w_syn_u2inh_exc_max'

    # v to inh neuron, inhibition connection
    u2inh_inhibition = Synapses(temporal_layer, target=inhibition_neuron, method=diff_method,
                                on_pre='''
                                s_inh += w_syn
                                A_pre = (- w_syn) * A_minus * (1 - 1/tau_minus) * time_post
                                w_syn = clip(w_syn + plasticity * A_pre, 0, w_syn_u2inh_inh_max) 
                                ''',
                                on_post='''
                                A_post = exp(-w_syn) * A_plus * (1 - 1/tau_plus) * time_pre
                                w_syn = clip(w_syn + plasticity * A_post, 0, w_syn_u2inh_inh_max)
                                ''',
                                model='''
                                w_syn : 1 # synaptic weight / synapse efficacy 
                                plasticity : boolean (shared)
                                ''')
    u2inh_inhibition.connect(i=np.arange(N), j=0)
    u2inh_inhibition.w_syn = 'rand() * w_syn_u2inh_inh_max'

    # inh neuron to v, inhibition connection
    inh2u_inhibition = Synapses(inhibition_neuron, target=temporal_layer, method=diff_method,
                                on_pre='''
                                s_inh2u += w_syn
                                A_pre = (- w_syn) * A_minus * (1 - 1/tau_minus) * time_post
                                w_syn = clip(w_syn + plasticity * A_pre, 0, w_syn_inh2u_max)
                                ''',
                                on_post='''
                                A_post = exp(-w_syn) * A_plus * (1 - 1/tau_plus) * time_pre
                                w_syn = clip(w_syn + plasticity * A_post, 0, w_syn_inh2u_max)
                                ''',
                                model='''
                                w_syn : 1 # synaptic weight / synapse efficacy
                                plasticity : boolean (shared)
                                ''')
    inh2u_inhibition.connect(i=0, j=np.arange(N))
    # inh2u_inhibition.w_syn = 'rand() * w_syn_inh2u_max'
    inh2u_inhibition.w_syn = 0.5 * w_syn_inh2u_max
    # som lateral connection
    som_synapse = Synapses(som_layer, target=som_layer, method=diff_method,
                           on_pre='''
                           radius = X - (X - X_)/(1+(2**0.5 - 1)*((global_time/T)**(2 * power_n)))
                           
                           y_pre = floor(i / map_size)
                           x_pre = i - y_pre * map_size
                           
                           y_post = floor(j/map_size)
                           x_post = j - y_post * map_size
                            
                           dist = (x_post - x_pre)**2 + (y_post - y_pre)**2
                           
                           G1 = (1 + a) * exp(- dist/(radius**2)) / (2 * pi * radius**2)
                           G2 = a * exp(- dist/(b * radius)**2) / (2 * pi * (b * radius)**2)
                           
                           w_syn = clip(G1 + G2, 0, w_syn_som_to_som_max)
                           s_lateral += w_syn
                           ''',
                           on_post='''
                           ''',
                           model='''
                           w_syn : 1 # synaptic weight / synapse efficacy
                           ''')
    som_synapse.connect(condition='i!=j')
    # som afferent connection
    temporal_to_som_synapse = Synapses(temporal_layer, target=som_layer, method=diff_method,
                                       on_pre='''
                                       s_afferent += w_syn
                                       A_pre = (- w_syn) * A_minus * (1 - 1/tau_minus) ** time_post
                                       w_syn = clip(w_syn + plasticity * A_pre, 0,  w_syn_temporal_to_som_max)
                                       ''',
                                       on_post='''
                                       A_post = exp(-w_syn) * A_plus * (1 - 1/tau_plus) * time_pre
                                       w_syn = clip(w_syn + plasticity * A_post, 0,  w_syn_temporal_to_som_max)
                                       ''',
                                       model='''
                                       w_syn : 1 # synaptic weight / synapse efficacy
                                       plasticity : boolean (shared)
                                       ''')
    temporal_to_som_synapse.connect()
    temporal_to_som_synapse.w_syn = np.random.randint(low=40000, high=60000, size=N*map_size*map_size) \
                                    * w_syn_temporal_to_som_max / 100000.0

    # Visualization

    som_spike_mon = SpikeMonitor(som_layer)

    u_spike_mon = SpikeMonitor(temporal_layer)
    # u_state_mon_v = StateMonitor(temporal_layer, 'v', record=True)
    # u_state_mon_time = StateMonitor(temporal_layer, 'time', record=True)
    # u_state_mon_w = StateMonitor(temporal_layer, 'w_inh2u', record=True)

    inh_spike_mon = SpikeMonitor(inhibition_neuron)
    # inh_state_mon = StateMonitor(inhibition_neuron, 'v', record=True)
    # w_exc_neu_state = StateMonitor(inhibition_neuron, 'w_exc', record=True)
    # w_inh_neu_state = StateMonitor(inhibition_neuron, 'w_inh', record=True)
    #
    # w_syn_u2inh_exc = StateMonitor(u2inh_excitation, 'w_syn', record=True)

    defaultclock.dt = time_step * ms

    step = 2

    plasticity_state = False

    u2inh_excitation.plasticity = plasticity_state
    u2inh_inhibition.plasticity = plasticity_state
    inh2u_inhibition.plasticity = plasticity_state
    temporal_to_som_synapse.plasticity = True  # plasticity_state

    # simulation_time = 200
    # run(simulation_time * ms, report='text')
    # weight visualization

    # simulation
    simulation_time = 50
    attempts = 5
    dataset = ArtificialDataSet(500, int(N/10))
    dataset = dataset.generate_set()
    np.savetxt('dataset.txt', dataset, delimiter=';')
    plt.scatter(dataset[:, 0], dataset[:, 1], s=5)
    plt.show()

    net_model = Network(collect())
    net_model.store()
    for vector in dataset:
        for it in range(attempts):
            net_model.restore()
            print("Input vector: {0}, attempt: {1}".format(vector, it))
            potential_input = rf.float_to_membrane_potential(vector)
            potential_input = potential_input.flatten()
            temporal_layer.I_ext = potential_input
            net_model.run(simulation_time * ms, report='text')
            net_model.store()

    # visual
    app = QtGui.QApplication([])
    win = pg.GraphicsWindow(title="som")
    win.resize(1000, 600)
    win.setWindowTitle('brain')
    # Enable antialiasing for prettier plots
    pg.setConfigOptions(antialias=True)

    p1 = win.addPlot(title="Region Selection")

    p1.plot(u_spike_mon.t / ms, u_spike_mon.i[:], pen=None, symbol='o',
            symbolPen=None, symbolSize=5, symbolBrush=(255, 255, 255, 255))
    p1.showGrid(x=True, y=True)
    lr = pg.LinearRegionItem([0, simulation_time])
    lr.setZValue(0)
    p1.addItem(lr)
    p2 = win.addPlot(title="Zoom on selected region")
    p2.plot(u_spike_mon.t / ms, u_spike_mon.i[:], pen=None, symbol='o',
            symbolPen=None, symbolSize=5, symbolBrush=(255, 255, 255, 255))
    p2.showGrid(x=True, y=True)
    def updatePlot():
        p2.setXRange(*lr.getRegion(), padding=0)
    def updateRegion():
        lr.setRegion(p2.getViewBox().viewRange()[0])
    lr.sigRegionChanged.connect(updatePlot)
    p2.sigXRangeChanged.connect(updateRegion)
    updatePlot()

    win.nextRow()

    p3 = win.addPlot(title="Region Selection")
    p3.plot(som_spike_mon.t / ms, som_spike_mon.i[:], pen=None, symbol='o',
            symbolPen=None, symbolSize=5, symbolBrush=(255, 255, 255, 255))
    p3.showGrid(x=True, y=True)
    lr1 = pg.LinearRegionItem([0, 10])
    lr1.setZValue(0)
    p3.addItem(lr1)
    p4 = win.addPlot(title="Zoom on selected region")
    p4.plot(som_spike_mon.t / ms, som_spike_mon.i[:], pen=None, symbol='o',
            symbolPen=None, symbolSize=5, symbolBrush=(255, 255, 255, 255))
    p4.showGrid(x=True, y=True)
    def updatePlot2():
        p4.setXRange(*lr1.getRegion(), padding=0)
    def updateRegion2():
        lr1.setRegion(p4.getViewBox().viewRange()[0])
    lr1.sigRegionChanged.connect(updatePlot2)
    p4.sigXRangeChanged.connect(updateRegion2)
    updatePlot2()

    u2som_syn_shape = temporal_to_som_synapse.w_syn[:].shape
    picture = temporal_to_som_synapse.w_syn[:].reshape(N, int(u2som_syn_shape[0] / N))

    np.savetxt('weights.txt', picture, delimiter=';')

    win2 = QtGui.QMainWindow()
    win2.resize(800, 800)
    imv = pg.ImageView()
    win2.setCentralWidget(imv)
    win2.show()
    win2.setWindowTitle("SOM weights")
    imv.setImage(picture)


    # subplot(421)
    # # subplot(111)
    # title("Temporal layer spikes")
    # plot(u_spike_mon.t / ms, u_spike_mon.i, '.k')
    # xlabel('Time (ms)')
    # ylabel('Neuron index')
    # grid(True)
    # xticks(np.arange(0.0, simulation_time + step, step))
    # yticks(np.arange(-1, N + 1, 1))
    #
    # # show()
    #
    # subplot(422)
    # title("Inhibition neuron spikes")
    # plot(inh_spike_mon.t / ms, inh_spike_mon.i, '.k')
    # xlabel('Time (ms)')
    # ylabel('Neuron index')
    # grid(True)
    # xticks(np.arange(0.0, simulation_time + step, step))
    # yticks(np.arange(-1, 1, 1))
    #
    # subplot(423)
    # title("u membrane potential")
    # for item in u_state_mon_v:
    #     plot(u_state_mon_v.t / ms, item.v)
    # # plot(u_state_mon_v.t / ms, u_state_mon_v[0].v)
    # xlabel('Time (ms)')
    # ylabel('Potential')
    # xticks(np.arange(0.0, simulation_time + step, step))
    #
    # subplot(424)
    # title("Inhibition neuron membrane potential")
    # plot(inh_state_mon.t / ms, inh_state_mon[0].v)
    # xlabel('Time (ms)')
    # ylabel('Potential')
    # xticks(np.arange(0.0, simulation_time + step, step))
    #
    # subplot(425)
    # title("Excitation/inhibition interaction")
    # plot(w_exc_neu_state.t / ms, w_exc_neu_state[0].w_exc, w_exc_neu_state.t / ms, w_inh_neu_state[0].w_inh,
    #      w_exc_neu_state.t / ms, w_exc_neu_state[0].w_exc - w_inh_neu_state[0].w_inh)
    # xlabel('Time (ms)')
    # ylabel('Potential')
    # xticks(np.arange(0.0, simulation_time + step, step))
    #
    # subplot(426)
    # title("Inhibition to u potential")
    # plot(u_state_mon_w.t / ms, u_state_mon_w[0].w_inh2u)
    # xlabel('Time (ms)')
    # ylabel('Potential')
    # xticks(np.arange(0.0, simulation_time + step, step))
    #
    # subplot(427)
    # title("Synaptic Weight")
    # for item in w_syn_u2inh_exc:
    #     plot(w_syn_u2inh_exc.t / ms, item.w_syn)
    # xlabel('Time (ms)')
    # ylabel('Potential')
    # xticks(np.arange(0.0, simulation_time + step, step))
    # yticks(np.arange(-0.1, 1.1, 0.1))
    #
    # subplot(428)
    # title("Synaptic time pre spike")
    # for item in u_state_mon_time:
    #     plot(w_syn_u2inh_exc.t / ms, item.time)
    # xlabel('Time (ms)')
    # ylabel('Potential')
    # xticks(np.arange(0.0, simulation_time + step, step))
    #
    # show()
    #
    # # subplot(111)
    # title("Som layer spikes")
    # plot(som_spike_mon.t / ms, som_spike_mon.i, '.k')
    # xlabel('Time (ms)')
    # ylabel('Neuron index')
    # grid(True)
    # xticks(np.arange(0.0, simulation_time + step, step))
    # yticks(np.arange(-1, map_size * map_size + 1, 1))
    #
    # show()

if __name__ == '__main__':
    import sys
    if (sys.flags.interactive != 1) or not hasattr(QtCore, 'PYQT_VERSION'):
        QtGui.QApplication.instance().exec_()
