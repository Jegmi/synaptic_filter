#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classes, functions for Synaptic Filter
Created on Sun 17 Jan 2021
@author: jannes
"""

import numpy as np


def init(p,mu_0 = None, sig2_0=None,t_num=None):
    v = {}
    dim = p['dim']
    t_num = p['t_num'] if t_num is None else t_num

    # other
    v['alpha'] = np.zeros(t_num) # spike response kernel
    v['x'] = np.zeros((t_num, dim))
    v['Sx'] = np.zeros((t_num, dim))
    v['w'] = np.zeros((t_num, dim))
    v['g'] = np.ones(t_num) * p['g0'] * p['dt']
    v['ev1'] = np.ones(t_num) * 1
    v['u'] = np.zeros(t_num)
    v['gbar'] = np.ones(t_num) * p['g0'] * p['dt']
    v['gmap'] = np.ones(t_num) * p['g0'] * p['dt']  # compute without variance
    v['y'] = np.zeros(t_num)
    v['xdot'] = np.zeros((t_num, dim))
    v['d'] = np.zeros((t_num, dim)) # spike vector
    v['x_wiggle'] = np.zeros((t_num, dim)) # average input vector

    # weights
    v['w'][0] = p['mu_ou'] + np.random.randn(p['dim']) * p['sig2_ou']**0.5

    # mean
    v['mu'] = np.zeros((t_num, dim))
    if mu_0 is None:
        v['mu'][0] = np.ones(dim) * p['mu_ou']

        if p['include-bias'] == True:
            v['mu'][0,0] = p['mu_oub'] # bias
    else:
        v['mu'][0] = mu_0.copy()

    # init sig2

    # exp
    if p['rule'] == 'exp':
        v['sig2'] = np.zeros((t_num, dim))
        if sig2_0 is None:
            v['sig2'][0] = np.ones(dim)*p['sig2_ou']
        else:
            v['sig2'][0] = sig2_0.copy()

    # corr
    if p['rule'] == 'corr':
        v['sig2'] = np.zeros((t_num, dim, dim))
        if sig2_0 is None:
            v['sig2'][0] = np.diag(np.ones(dim)*p['sig2_ou'])
        else:
            v['sig2'][0] = sig2_0.copy()

    # exp-rm and exp-z
    elif (('exp-z' == p['rule']) or ('exp-rm' == p['rule'])):
        v['sig2'] = np.zeros((t_num, dim))
        if sig2_0 is None:
            if p['include-bias'] == True:
                v['sig2'][0,0] = p['mu_oub'] # only bias non-zero
            else:
                v['sig2'][0,0] = 0 #p['mu_ou']
        else:
            v['sig2'][0] = sig2_0.copy()

    # exp-rm2, assume no bias in this case
    elif 'exp-rm2' == p['rule']:
        v['sig2'] = np.zeros((t_num, dim))
        v['d'][0] = 0
        v['x_wiggle'][0] = 0

    # oja
    elif 'oja' in p['rule']:
        v['sig2'] = np.zeros((t_num, dim))
        v['ev1'][0] = 1
        if sig2_0 is None:
            v['sig2'][0,0] = p['sig2_ou']
        else:
            v['sig2'][0] = sig2_0.copy()
    return v


def init_pre_post_protocol(v,p,wait=0.5):

    idx_post = np.array(np.round((wait + np.abs(p['delta_T']))/p['dt']),dtype=int)
    idx_pre = np.array(np.round(wait/p['dt']),dtype=int)

    # only first synapse
    if p['include-bias'] == True:
        dim = 1
    else:
        dim = 0

    if p['delta_T'] > 0:
        v['Sx'][idx_pre,dim] = 1
        v['y'][idx_post] = 1
    else:
        v['Sx'][idx_post,dim] = 1
        v['y'][idx_pre] = 1
    return v


def init_correlated_protocol(v,p, wait=0.5):

    # add correlated protocol for all synapses
    idx_spikes = np.array(np.round((wait + np.array(p['correlated_times']))/p['dt']),dtype=int)
    v['Sx'][idx_spikes] = 1

    # add STDP protocol
    # wait period for STDP (measured from t=0)
    wait_STDP = 2*wait + p['correlated_times'][-1]
    init_pre_post_protocol(v,p,wait=wait_STDP)

    return v, wait_STDP
