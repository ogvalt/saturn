import numpy as np
from brian2 import *


class ReceptiveField:
    # Parameter that used in standard deviation definition
    gamma = 0.8

    def __init__(self, bank_size=10, I_min=0.0, I_max=1.0):
        self.bank_size = bank_size
        self.field_mu = np.array([(I_min + ((2 * i - 2) / 2) * ((I_max - I_min) / (bank_size - 1)))
                                  for i in range(1, bank_size + 1)])
        self.field_sigma = (1.0 / self.gamma) * ((I_max - I_min))

    def float_to_membrane_potential(self, input_vector):
        try:
            input_vector = input_vector.reshape((input_vector.shape[0], 1))
        except Exception as e:
            print("Exception: {0}\nObject shape: {1}".format(repr(e), input_vector.shape))
            exit(1)

        temp = np.exp(-((input_vector - self.field_mu) ** 2) / (2 * self.field_sigma * self.field_sigma))
        # temp += np.exp(-((input_vector - 1 - self.field_mu) ** 2) / (2 * self.field_sigma * self.field_sigma))
        # temp += np.exp(-((input_vector + 1 - self.field_mu) ** 2) / (2 * self.field_sigma * self.field_sigma))
        temp = temp.astype(np.float16)

        return temp


# class SpikingSOM:
#
#     def __init__(self, inst_receptive_field, prototype_dim=3):
#         self.receptive_field = inst_receptive_field
#         self.prototype_dimention = prototype_dim
#
#     def float_to_temporal_layer(self):
#
#         tau_m = 1*ms
#         u_rest = 0.0*mV
#         equation = '''
#                     dv/dt = (I_input + u_rest)/tau_m : volt
#                    '''


if __name__ == "__main__":
    rf = ReceptiveField(I_min=0.05, I_max=0.95)
    print(rf.field_mu)
    # vect = np.array([0.15, 0.07, 0.1])
    #
    # print(rf.float_to_membrane_potential(vect))
    # inputs = np.random.rand(3)
    inputs = np.array([0.40, 0.95, 0.77])
    # inputs = np.array([0.4])
    np.random.seed(seed=1)

    N = 30
    time_step = 0.01

    A_plus = 0.0016
    A_minus = 0.0055

    tau_plus = 11
    tau_minus = 10

    # inputs = np.random.rand(3, 1)
    potential_input = rf.float_to_membrane_potential(inputs)
    potential_input = potential_input.flatten()
    diff_method = 'euler'

    w_syn_u2inh_exc_max = 1.0
    w_syn_u2inh_inh_max = 1.0
    w_syn_inh2u_max = 100.0

    teta_reset_u = -0.5
    # temporal layer
    tau_m = 1.0 * ms
    tau_r_inh2u = 1.0 * ms
    tau_f_inh2u = 5.0 * ms
    teta_u = 0.5
    # inh neuron
    tau_inh = 0.5 * ms

    tau_r_exc = 0.4 * ms
    tau_f_exc = 2.0 * ms

    tau_r_inh = 0.2 * ms
    tau_f_inh = 1.0 * ms

    teta_u_inh = 0.01
    teta_reset_inh = -0.1

    equ = '''
        drr/dt = 1 / ms : 1
        
        # inhibition connection to u layer
        
        ds_inh2u/dt = (-s_inh2u)/tau_r_inh2u: 1
        dw_inh2u/dt = (s_inh2u - w_inh2u)/tau_f_inh2u: 1

        # membrane potential of u layer
        
        dv/dt = (-v + I_ext - w_inh2u) / tau_m: 1
        I_ext : 1
    '''

    temporal_layer = NeuronGroup(N, equ, threshold='v>teta_u', method=diff_method,
                                 reset='''v = teta_reset_u; rr = 0''')

    temporal_layer.I_ext = potential_input
    # temporal_layer.I_ext = 0.4
    # inhibition neuron

    inh_equ = '''
        drr/dt = 1 / ms : 1
        
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
        dv/dt = (-v + w_exc - w_inh) / tau_inh: 1
    '''
    inhibition_neuron = NeuronGroup(1, inh_equ, method=diff_method, threshold='v>teta_u_inh',
                                    reset='''
                                            v = teta_reset_inh
                                            rr = 0 
                                            ''')

    # v to inh neuron, excitation connection
    u2inh_excitation = Synapses(temporal_layer, target=inhibition_neuron, method=diff_method,
                                on_pre='''
                                s_exc += w_syn
                                Apre = (- w_syn) * A_minus * (1 - 1/tau_minus) ** rr_post
                                w_syn = clip(w_syn + plasticity * Apre, 0, w_syn_u2inh_exc_max) 
                                ''',
                                on_post='''
                                Apost = exp(-w_syn) * A_plus * (1 - 1/tau_plus) ** rr_pre
                                w_syn = clip(w_syn + plasticity * Apost, 0, w_syn_u2inh_exc_max)
                                ''',
                                model='''
                                w_syn : 1 # synaptic weight / synapse efficacy
                                plasticity : boolean (shared)
                                ''')
    u2inh_excitation.connect(i=np.arange(N), j=0)
    # u2inh_excitation.w_syn = 'rand() * w_syn_u2inh_exc_max'
    u2inh_excitation.w_syn = np.random.rand(N) * w_syn_u2inh_exc_max

    # v to inh neuron, inhibition connection
    u2inh_inhibition = Synapses(temporal_layer, target=inhibition_neuron, method=diff_method,
                                on_pre='''
                                s_inh += w_syn
                                Apre = (- w_syn) * A_minus * (1 - 1/tau_minus) * rr_post
                                w_syn = clip(w_syn + plasticity * Apre, 0, w_syn_u2inh_inh_max) 
                                ''',
                                on_post='''
                                Apost = exp(-w_syn) * A_plus * (1 - 1/tau_plus) * rr_pre
                                w_syn = clip(w_syn + plasticity * Apost, 0, w_syn_u2inh_inh_max)
                                ''',
                                model='''
                                w_syn : 1 # synaptic weight / synapse efficacy 
                                plasticity : boolean (shared)
                                ''')

    u2inh_inhibition.connect(i=np.arange(N), j=0)
    # u2inh_inhibition.w_syn = 'rand() * w_syn_u2inh_inh_max'
    u2inh_inhibition.w_syn = np.random.rand(N) * w_syn_u2inh_inh_max
    # inh neuron to v, inhibition connection
    inh2u_inhibition = Synapses(inhibition_neuron, target=temporal_layer, method=diff_method,
                                on_pre='''
                                s_inh2u += w_syn
                                Apre = (- w_syn) * A_minus * (1 - 1/tau_minus) * rr_post
                                w_syn = clip(w_syn + plasticity * Apre, 0, w_syn_inh2u_max)
                                ''',
                                on_post='''
                                Apost = exp(-w_syn) * A_plus * (1 - 1/tau_plus) * rr_pre
                                w_syn = clip(w_syn + plasticity * Apost, 0, w_syn_inh2u_max)
                                ''',
                                model='''
                                w_syn : 1 # synaptic weight / synapse efficacy
                                plasticity : boolean (shared)
                                ''')
    inh2u_inhibition.connect(i=0, j=np.arange(N))
    # inh2u_inhibition.w_syn = 'rand() * w_syn_inh2u_max'
    inh2u_inhibition.w_syn = np.random.rand(1) * w_syn_inh2u_max

    tau_r_afferent = 0.2 * ms
    tau_f_afferent = 1.0 * ms

    tau_r_lateral = 0.1 * ms
    tau_f_lateral = 0.5 * ms

    tau_m_som = 1.0 * ms

    equ_som = '''
            dglobal_time/dt = 1 / ms : 1
            drr/dt = 1 / ms : 1

            # Afferent connection (from temporal layer to som layer)
            
            ds_afferent/dt = (-s_afferent)/tau_r_afferent: 1
            dw_afferent/dt = (s_afferent - w_afferent)/tau_f_afferent: 1 

            # lateral connection

            ds_lateral/dt = (-s_lateral)/tau_r_lateral: 1
            dw_lateral/dt = (s_lateral - w_lateral)/tau_f_lateral: 1

            # membrane potential of u layer

            dv/dt = (-v + w_lateral + w_afferent) / tau_m_som: 1
        '''

    map_size = 10

    teta_som = 1.0
    teta_reset_som = 0.0

    w_syn_temporal_to_som_max = 2.2
    w_syn_som_to_som_max = 1.0

    X = 3.0
    X_ = 3.0
    T = 1.0
    power_n = 1.0
    a = 3.0
    b = 3.0
    pi = np.pi

    som_layer = NeuronGroup(map_size * map_size, equ_som, threshold='v>teta_som', method=diff_method,
                            reset='''v = teta_reset_som; rr = 0''')

    som_synapse = Synapses(som_layer, target=som_layer, method=diff_method,
                           on_pre='''
                           radius = X - (X - X_)/(1+(2**0.5 - 1)*((T/global_time)**(2 * power_n)))
                           
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
    # som_synapse.w_syn = 'rand() * w_syn_som_to_som_max'

    temporal_to_som_synapse = Synapses(temporal_layer, target=som_layer, method=diff_method,
                                       on_pre='''
                                       s_afferent += w_syn
                                       Apre = (- w_syn) * A_minus * (1 - 1/tau_minus) ** rr_post
                                       w_syn = clip(w_syn + plasticity * Apre, 0,  w_syn_temporal_to_som_max)
                                       ''',
                                       on_post='''
                                       Apost = exp(-w_syn) * A_plus * (1 - 1/tau_plus) * rr_pre
                                       w_syn = clip(w_syn + plasticity * Apost, 0,  w_syn_temporal_to_som_max)
                                       ''',
                                       model='''
                                       w_syn : 1 # synaptic weight / synapse efficacy
                                       plasticity : boolean (shared)
                                       ''')

    temporal_to_som_synapse.connect()
    # temporal_to_som_synapse.w_syn = 'rand() * w_syn_temporal_to_som_max'

    temporal_to_som_synapse.w_syn = np.random.rand(3000) * w_syn_som_to_som_max

    # Visualization

    som_spike_mon = SpikeMonitor(som_layer)

    u_spike_mon = SpikeMonitor(temporal_layer)
    u_state_mon_v = StateMonitor(temporal_layer, 'v', record=True)
    u_state_mon_rr = StateMonitor(temporal_layer, 'rr', record=True)
    u_state_mon_w = StateMonitor(temporal_layer, 'w_inh2u', record=True)

    inh_spike_mon = SpikeMonitor(inhibition_neuron)
    inh_state_mon = StateMonitor(inhibition_neuron, 'v', record=True)
    w_exc_neu_state = StateMonitor(inhibition_neuron, 'w_exc', record=True)
    w_inh_neu_state = StateMonitor(inhibition_neuron, 'w_inh', record=True)

    w_syn_u2inh_exc = StateMonitor(u2inh_excitation, 'w_syn', record=True)

    defaultclock.dt = time_step * ms

    simulation_time = 40
    step = 0.2

    plasticity_state = True

    u2inh_excitation.plasticity = plasticity_state
    u2inh_inhibition.plasticity = plasticity_state
    inh2u_inhibition.plasticity = plasticity_state
    temporal_to_som_synapse.plasticity = plasticity_state

    run(simulation_time * ms, report='text')

    subplot(421)
    # subplot(111)
    title("Temporal layer spikes")
    plot(u_spike_mon.t / ms, u_spike_mon.i, '.k')
    xlabel('Time (ms)')
    ylabel('Neuron index')
    grid(True)
    xticks(np.arange(0.0, simulation_time + step, step))
    yticks(np.arange(-1, N + 1, 1))

    # show()

    subplot(422)
    title("Inhibition neuron spikes")
    plot(inh_spike_mon.t / ms, inh_spike_mon.i, '.k')
    xlabel('Time (ms)')
    ylabel('Neuron index')
    grid(True)
    xticks(np.arange(0.0, simulation_time + step, step))
    yticks(np.arange(-1, 1, 1))

    subplot(423)
    title("u membrane potential")
    for item in u_state_mon_v:
        plot(u_state_mon_v.t / ms, item.v)
    # plot(u_state_mon_v.t / ms, u_state_mon_v[0].v)
    xlabel('Time (ms)')
    ylabel('Potential')
    xticks(np.arange(0.0, simulation_time + step, step))

    subplot(424)
    title("Inhibition neuron membrane potential")
    plot(inh_state_mon.t / ms, inh_state_mon[0].v)
    xlabel('Time (ms)')
    ylabel('Potential')
    xticks(np.arange(0.0, simulation_time + step, step))

    subplot(425)
    title("Excitation/inhibition interaction")
    plot(w_exc_neu_state.t / ms, w_exc_neu_state[0].w_exc, w_exc_neu_state.t / ms, w_inh_neu_state[0].w_inh,
         w_exc_neu_state.t / ms, w_exc_neu_state[0].w_exc - w_inh_neu_state[0].w_inh)
    xlabel('Time (ms)')
    ylabel('Potential')
    xticks(np.arange(0.0, simulation_time + step, step))

    subplot(426)
    title("Inhibition to u potential")
    plot(u_state_mon_w.t / ms, u_state_mon_w[0].w_inh2u)
    xlabel('Time (ms)')
    ylabel('Potential')
    xticks(np.arange(0.0, simulation_time + step, step))

    subplot(427)
    title("Synaptic Weight")
    for item in w_syn_u2inh_exc:
        plot(w_syn_u2inh_exc.t / ms, item.w_syn)
    xlabel('Time (ms)')
    ylabel('Potential')
    xticks(np.arange(0.0, simulation_time + step, step))
    yticks(np.arange(-0.1, 1.1, 0.1))

    subplot(428)
    title("Synaptic time pre spike")
    for item in u_state_mon_rr:
        plot(w_syn_u2inh_exc.t / ms, item.rr)
    xlabel('Time (ms)')
    ylabel('Potential')
    xticks(np.arange(0.0, simulation_time + step, step))

    show()

    # subplot(111)
    title("Som layer spikes")
    plot(som_spike_mon.t / ms, som_spike_mon.i, '.k')
    xlabel('Time (ms)')
    ylabel('Neuron index')
    grid(True)
    xticks(np.arange(0.0, simulation_time + step, step))
    yticks(np.arange(-1, map_size * map_size + 1, 1))

    show()
