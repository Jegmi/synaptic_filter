#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Classes, functions for Synaptic Filter
Created on Sun 17 Jan 2021
@author: jannes
"""

import numpy as np

def update_filter(v,p,k):

    dt = p['dt']
    if p['rule'] == 'exp':

        # like
        term1 = v['sig2'][k] * v['x'][k] * p['beta']

        # spike response kernel alpha = 0 by default
        u = (v['mu'][k].dot(v['x'][k]) - v['alpha'][k]) * p['beta']
        v['gmap'][k] = p['g0dt'] * np.exp(u)

        v['gbar'][k] = v['gmap'][k] * np.exp(v['sig2'][k].dot(v['x'][k]**2)*p['beta']**2 / 2)
        dmu_like = term1 * (v['y'][k] - v['gbar'][k])
        dsig2_like = -v['gbar'][k] * term1**2

        # prior for means and covariance
        dmu_pi = -(v['mu'][k] - p['mu_ou']) / p['tau_ou']
        dsig2_pi = np.ones(p['dim']) # init
        ## bias
        if p['include-bias'] == True:
            dmu_pi[0] = -(v['mu'][k, 0] - p['mu_oub']) / p['tau_oub']

            ## off-diag terms (inverse addition): (1/tau_b + 1/tau_w approx 1/tau_b)
            dsig2_pi = -(v['sig2'][k] - np.ones(p['dim']) * p['sig2_oub']) / p['tau_oub']

            # bias terms (fast)
            dsig2_pi[0, 0] = 2 * dsig2_pi[0, 0]
            i0 = 1
        else:
            i0 = 0

        dsig2_pi[i0:] = -2 * (v['sig2'][k, i0:] - np.ones(p['dim'])*p['sig2_ou']) / p['tau_ou']

        # update
        v['mu'][k+1] = v['mu'][k] + dmu_like + dmu_pi*dt
        v['sig2'][k+1] = v['sig2'][k] + dsig2_like + dsig2_pi*dt

    elif 'exp-oja' == p['rule']:

        # oja factor
        u_oja = v['sig2'][k].dot(v['x'][k])

        # update eigenvector (encoded in sig2)
        dsig2_like = u_oja*(v['x'][k] -  u_oja*v['sig2'][k])/p['tau_z']*p['dt']

        # update eigenvalue1
        dev1 = -(v['ev1'][k] - u_oja**2)/p['tau_z']*p['dt']
        v['ev1'][k+1] = v['ev1'][k] + dev1

        # covariance approx: sigma.dot(x)
        A3 = p['sig2_ou']*p['beta']**2*p['g0dt']/dt*p['tau_ou']*0.5
        vec_dot_x = v['sig2'][k].dot(v['x'][k])
        Sigma_x = p['sig2_ou']*(v['x'][k] - v['ev1'][k]*A3*vec_dot_x*v['sig2'][k])

        v['gmap'][k] = p['g0dt'] * np.exp(
            v['mu'][k].dot(v['x'][k]) * p['beta'])

        v['gbar'][k] = v['gmap'][k] * np.exp(
            v['x'][k].dot(Sigma_x) * p['beta']**2 / 2)

        dmu_like = p['beta']*Sigma_x* (v['y'][k] - v['gbar'][k])

        # prior for means and covariance
        dmu_pi = -(v['mu'][k] - p['mu_ou']) / p['tau_ou']

        ## bias
        if p['include-bias'] == True:
            dmu_pi[0] = -(v['mu'][k, 0] - p['mu_oub']) / p['tau_oub']

        # update
        v['mu'][k+1] = v['mu'][k] + dmu_like + dmu_pi*dt
        v['sig2'][k+1] = v['sig2'][k] + dsig2_like

    elif 'exp-rm' == p['rule']:

        dt = p['dt']
        A3 = p['sig2_ou']*p['beta']**2*p['g0dt']/dt*p['tau_ou']/2
        vec_dot_x = v['sig2'][k].dot(v['x'][k])
        Sigma_x = p['sig2_ou']*(v['x'][k] - A3*vec_dot_x*v['sig2'][k])

        v['gmap'][k] = p['g0dt'] * np.exp(
            v['mu'][k].dot(v['x'][k]) * p['beta'])
        v['gbar'][k] = v['gmap'][k] * np.exp(
            v['x'][k].dot(Sigma_x) * p['beta']**2 / 2)
        dmu_like = p['beta'] * (v['y'][k] - v['gbar'][k]) * Sigma_x
        dsig2_like = -(v['sig2'][k] - v['x'][k])/p['tau_z']*p['dt']

        # prior for means and covariance
        dmu_pi = -(v['mu'][k] - p['mu_ou']) / p['tau_ou']

        ## bias
        if p['include-bias'] == True:
            dmu_pi[0] = -(v['mu'][k, 0] - p['mu_oub']) / p['tau_oub']

        # update
        v['mu'][k+1] = v['mu'][k] + dmu_like + dmu_pi*dt
        v['sig2'][k+1] = v['sig2'][k] + dsig2_like


    elif 'exp-rm2' == p['rule']:

        eps0 = 1 # kernel prefactor

        dt = p['dt']
        # \bar{\alpha}
        A3 = p['sig2_ou']*p['beta']**2*p['g0dt']/dt*p['tau_ou']/2

        # compute sigma
        vec_dot_x = v['x_wiggle'][k].dot(v['x'][k])
        diag_times_x = (v['x_wiggle'][k] + v['d'][k])*v['x'][k]
        Sigma_x = p['sig2_ou']*(v['x'][k]
                    - A3*(vec_dot_x*v['x_wiggle'][k] + eps0/2*diag_times_x))

        if p['compute_sig2']: # only diagonal for now
            v['sig2'][k] = p['sig2_ou']*(1 - A3*(
                        v['x_wiggle'][k]**2 + eps0/2*diag_times_x)
                        )
            v['sig2'][k+1] = v['sig2'][k]

        if p['gamma_equal_g0']:
            v['gmap'][k] = p['g0dt']
            v['gbar'][k] = p['g0dt']
        else:
            v['gmap'][k] = p['g0dt'] * np.exp(
                v['mu'][k].dot(v['x'][k]) * p['beta'])
            v['gbar'][k] = v['gmap'][k] * np.exp(
                v['x'][k].dot(Sigma_x) * p['beta']**2 / 2)

        dmu_like = p['beta'] * (v['y'][k] - v['gbar'][k]) * Sigma_x

        # prior for means and covariance
        dmu_pi = -(v['mu'][k] - p['mu_ou']) / p['tau_ou']

        ## bias
        if p['include-bias'] == True:
            dmu_pi[0] = -(v['mu'][k, 0] - p['mu_oub']) / p['tau_oub']

        # updates
        v['mu'][k+1] = v['mu'][k] + dmu_like + dmu_pi*dt
        v['d'][k+1] = v['d'][k] + (-v['x'][k] - v['d'][k])*2/p['tau_d']*dt
        v['x_wiggle'][k+1] = v['x_wiggle'][k] -(v['x_wiggle'][k] - v['x'][k])/p['tau_x_wiggle']*p['dt']


    # no cross talk between synapses and bias
    if p['rule'] == 'exp-z':

        # like

        ## beta * z
        term1 = v['sig2'][k] * p['beta']  #OK

        # spike response kernel alpha = 0 by default
        u = (v['mu'][k].dot(v['x'][k]) - v['alpha'][k]) * p['beta']
        v['gmap'][k] = p['g0dt'] * np.exp(u) #OK

        ## x Sig x = z_/0*x_/0 + z_0*1
        v['gbar'][k] = v['gmap'][k] * np.exp(v['sig2'][k].dot(v['x'][k]) * p['beta']**2 / 2)  #OK

        dmu_like = term1 * (v['y'][k] - v['gbar'][k]) * v['x'][k] # OK
        dsig2_like = dmu_like.copy() # dummy

        if p['include-bias'] == True:
            dsig2_like[0] = -v['gbar'][k] * term1[0]**2 # OK
            i0 = 1
        else:
            i0 = 0
        dsig2_like[i0:] = -v['gbar'][k] * term1[i0:].dot(v['x'][k,i0:]) * term1[i0:] # OK

        # prior
        dmu_pi = -(v['mu'][k] - p['mu_ou']) / p['tau_ou'] # OK

        if p['include-bias'] == True:
            dmu_pi[0] = -(v['mu'][k, 0] - p['mu_oub']) / p['tau_oub'] # OK

        ## sig2_ou is diagonal matrix, here scalar
        dsig2_pi = dmu_pi.copy() # dummy

        # bias:
        if p['include-bias'] == True:
            dsig2_pi[0] = - 2 * (v['sig2'][k,0] - p['sig2_oub']) / p['tau_oub']
            i0 = 1
        else:
            i0 = 0

        ## alpha
        A = p['beta']**2*p['g0dt']/dt*p['tau_ou'] # OK
        dsig2_pi[i0:] = -2 * (v['sig2'][k,i0:] - p['sig2_ou']*v['x'][k,i0:]
                         ) / p['tau_ou'] + (p['sig2_ou']*v['xdot'][k,i0:] -
                         A*v['sig2'][k,i0:].dot(v['xdot'][k,i0:])*v['sig2'][k,i0:]) # OK

        # update
        v['mu'][k+1] = v['mu'][k] + dmu_like + dmu_pi*dt
        v['sig2'][k+1] = v['sig2'][k] + dsig2_like + dsig2_pi*dt


    elif p['rule'] == 'corr':

        # like
        term1 = v['sig2'][k].dot(v['x'][k]) * p['beta']

        # spike response kernel alpha = 0 by default
        u = (v['mu'][k].dot(v['x'][k]) - v['alpha'][k]) * p['beta']
        v['gmap'][k] = p['g0dt'] * np.exp(u)

        v['gbar'][k] = v['gmap'][k] * np.exp(v['x'][k].dot(v['sig2'][k].dot(v['x'][k]))*p['beta']**2 / 2)
        dmu_like = term1 * (v['y'][k] - v['gbar'][k])
        dsig2_like = -v['gbar'][k] * term1[np.newaxis,:]*term1[:,np.newaxis]

        # prior for means and covariance
        dmu_pi = -(v['mu'][k] - p['mu_ou']) / p['tau_ou']
        dsig2_pi = np.diag(np.ones(p['dim'])) # init
        ## bias
        if p['include-bias'] == True:
            dmu_pi[0] = -(v['mu'][k, 0] - p['mu_oub']) / p['tau_oub']

            ## off-diag terms (inverse addition): (1/tau_b + 1/tau_w approx 1/tau_b)
            dsig2_pi = -(v['sig2'][k] - np.diag(np.ones(p['dim']) * p['sig2_oub'])) / p['tau_oub']

            # bias terms (fast)
            dsig2_pi[0, 0] = 2 * dsig2_pi[0, 0]
            i0 = 1
        else:
            i0 = 0

        dsig2_pi[i0:, i0:] = -2 * (v['sig2'][k, i0:, i0:] - np.diag(np.ones(p['dim'])*p['sig2_ou'])) / p['tau_ou']

        # update
        v['mu'][k+1] = v['mu'][k] + dmu_like + dmu_pi*dt
        v['sig2'][k+1] = v['sig2'][k] + dsig2_like + dsig2_pi*dt


def update_protocol(v,p,k):
    """ call before filter update """

    # update world
    dt = p['dt']
    v['x'][k] += v['Sx'][k]  # init cond is zero for entire array
    v['x'][k + 1] = (1 - dt / p['tau']) * v['x'][k]
    v['xdot'][k] += v['Sx'][k]/dt
    v['xdot'][k+1] = - v['x'][k]*dt/p['tau']

    # bias
    if p['include-bias'] == True:
        v['x'][k+1,0], v['x'][k,0] = 1, 1
        v['xdot'][k+1,0], v['xdot'][k,0] = 0, 0

    # spike response kernel:
    if p['include-spike-response-kernel'] == True:
        #v['alpha'][k] += p['amplitude_alpha']*v['y'][k]  # init cond is zero for entire array
        v['alpha'][k + 1] = (1 - dt / p['tau_alpha']) * v['alpha'][k] + p['amplitude_alpha']*v['y'][k]
    else:
        v['alpha'][k + 1], v['alpha'][k] = 0, 0


def update_generator(v,p,k):
    """ call before protocol """
    dt = p['dt']

    # propagate weights
    dW = (dt * p['sig2_ou'] / p['tau_ou'] * 2)**0.5
    v['w'][k+1] = v['w'][k] + dt / p['tau_ou'] * (
                p['mu_ou'] - v['w'][k]) + dW * np.random.randn(p['dim'])    # np.random.randn(p['dim-gm'])

    # generate input spikes randomly
    v['Sx'][k] = np.random.binomial(1,p['rate']*p['dt'],p['dim'])

    # generate output spikes
    u = v['w'][k].dot(v['x'][k]) - v['alpha'][k]
    v['g'][k] = p['g0']*np.exp( p['beta']*u)

    # catch
    assert not np.isnan(v['g'][k])
    gdt = v['g'][k]*p['dt']
    gdt_gg_one = gdt > 1
    if gdt_gg_one is True:
        gdt = 1
    v['y'][k] = np.random.binomial(1,min(gdt,1))
    return {'gdt_gg_one':gdt_gg_one}
