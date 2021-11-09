# -*- coding: utf-8 -*-
#
# This file is part of the pyFDA project hosted at https://github.com/chipmuenk/pyfda
#
# Copyright © pyFDA Project Contributors
# Licensed under the terms of the MIT License
# (see file LICENSE in root directory for details)

"""
Widget for specifying the parameters of a direct-form DF1 FIR filter
"""
import sys

import numpy as np
from numpy.lib.function_base import iterable
import pyfda.filterbroker as fb
from pyfda.libs.pyfda_lib import set_dict_defaults, pprint_log
from pyfda.libs.pyfda_qt_lib import qget_cmb_box

from pyfda.libs.compat import QWidget, QVBoxLayout, pyqtSignal

import pyfda.libs.pyfda_fix_lib as fx
from pyfda.fixpoint_widgets.fixpoint_helpers import UI_W, UI_Q
from pyfda.fixpoint_widgets.fixpoint_helpers_nmigen import requant

#####################
from functools import reduce
from operator import add

# from migen import Signal, Module, run_simulation
# from migen.fhdl import verilog

from nmigen import *
# from nmigen import Signal, signed
# from nmigen.build.plat import Platform
# from nmigen.hdl import ast, dsl, ir
# from nmigen.sim.core import Simulator, Tick, Delay
from nmigen.sim import Simulator, Tick  # , Delay, Settle
# from nmigen.build import Platform
# from nmigen.back.pysim import Simulator, Delay, Settle

################################

import logging
logger = logging.getLogger(__name__)

classes = {'FIR_DF_NM_ui': 'FIR_DF_nm'}  #: Dict containing widget class name : display name


# =============================================================================
class FIR_DF_NM_ui(QWidget):
    """
    Widget for entering word formats & quantization, also instantiates fixpoint
    filter class :class:`FilterFIR`.
    """
    sig_rx = pyqtSignal(object)  # incoming
    sig_tx = pyqtSignal(object)  # outcgoing
    from pyfda.libs.pyfda_qt_lib import emit

    def __init__(self, parent=None):
        super(FIR_DF_NM_ui, self).__init__(parent)

        self.title = ("<b>Direct-Form (DF) FIR Filter</b><br />"
                      "Standard FIR topology.")
        self.img_name = "fir_df.png"

        self._construct_UI()
        # Construct an instance of the fixpoint filter using the settings from
        # the 'fxqc' quantizer dict
        # TODO: not needed, remove test in input_fixpoint_specs
        # self.construct_fixp_filter()
# ------------------------------------------------------------------------------

    def _construct_UI(self):
        """
        Intitialize the UI with widgets for coefficient format and input and
        output quantization
        """
        if 'QA' not in fb.fil[0]['fxqc']:
            fb.fil[0]['fxqc']['QA'] = {}
        set_dict_defaults(fb.fil[0]['fxqc']['QA'],
                          {'WI': 0, 'WF': 30, 'W': 32, 'ovfl': 'wrap', 'quant': 'floor'})

        self.wdg_w_coeffs = UI_W(self, fb.fil[0]['fxqc']['QCB'], wdg_name='w_coeff',
                                 label='Coeff. Format <i>B<sub>I.F&nbsp;</sub></i>:',
                                 tip_WI='Number of integer bits - edit in "b,a" tab',
                                 tip_WF='Number of fractional bits - edit in "b,a" tab',
                                 WI=fb.fil[0]['fxqc']['QCB']['WI'],
                                 WF=fb.fil[0]['fxqc']['QCB']['WF'])


#        self.wdg_q_coeffs = UI_Q(self, fb.fil[0]['fxqc']['QCB'],
#                                        cur_ov=fb.fil[0]['fxqc']['QCB']['ovfl'],
#                                        cur_q=fb.fil[0]['fxqc']['QCB']['quant'])
#        self.wdg_q_coeffs.sig_tx.connect(self.update_q_coeff)

        self.wdg_w_accu = UI_W(self, fb.fil[0]['fxqc']['QA'],
                               label='', wdg_name='w_accu',
                               fractional=True, combo_visible=True)

        self.wdg_q_accu = UI_Q(self, fb.fil[0]['fxqc']['QA'], wdg_name='q_accu',
                               label='Accu Format <i>Q<sub>A&nbsp;</sub></i>:')

        # initial setting for accumulator
        cmbW = qget_cmb_box(self.wdg_w_accu.cmbW, data=False)
        self.wdg_w_accu.ledWF.setEnabled(cmbW == 'man')
        self.wdg_w_accu.ledWI.setEnabled(cmbW == 'man')

        # ----------------------------------------------------------------------
        # LOCAL SIGNALS & SLOTs & EVENTFILTERS
        # ----------------------------------------------------------------------
        self.wdg_w_coeffs.sig_tx.connect(self.update_q_coeff)
        self.wdg_w_accu.sig_tx.connect(self.process_sig_rx)
        self.wdg_q_accu.sig_tx.connect(self.process_sig_rx)
# ------------------------------------------------------------------------------

        layVWdg = QVBoxLayout()
        layVWdg.setContentsMargins(0, 0, 0, 0)

        layVWdg.addWidget(self.wdg_w_coeffs)
#        layVWdg.addWidget(self.wdg_q_coeffs)
        layVWdg.addWidget(self.wdg_q_accu)
        layVWdg.addWidget(self.wdg_w_accu)

        layVWdg.addStretch()

        self.setLayout(layVWdg)

# ------------------------------------------------------------------------------
    def process_sig_rx(self, dict_sig=None):
        logger.debug("sig_rx:\n{0}".format(pprint_log(dict_sig)))
        # check whether anything needs to be done locally
        # could also check here for 'quant', 'ovfl', 'WI', 'WF' (not needed at the moment)
        # if not, just pass the dict.
        if 'ui' in dict_sig:
            if dict_sig['wdg_name'] == 'w_coeff':  # coefficient format updated
                """
                Update coefficient quantization settings and coefficients.

                The new values are written to the fixpoint coefficient dict as
                `fb.fil[0]['fxqc']['QCB']` and  `fb.fil[0]['fxqc']['b']`.
                """

                fb.fil[0]['fxqc'].update(self.ui2dict())

            elif dict_sig['wdg_name'] == 'cmbW':
                cmbW = qget_cmb_box(self.wdg_w_accu.cmbW, data=False)
                self.wdg_w_accu.ledWF.setEnabled(cmbW == 'man')
                self.wdg_w_accu.ledWI.setEnabled(cmbW == 'man')
                if cmbW in {'full', 'auto'}:
                    self.dict2ui()
                    self.emit({'specs_changed': 'cmbW'})
                else:
                    return

            dict_sig.update({'id': id(self)})  # currently only local

        self.emit(dict_sig)

# ------------------------------------------------------------------------------
    def update_q_coeff(self, dict_sig):
        """
        Update coefficient quantization settings and coefficients.

        The new values are written to the fixpoint coefficient dict as
        `fb.fil[0]['fxqc']['QCB']` and
        `fb.fil[0]['fxqc']['b']`.
        """
        logger.debug("update q_coeff - dict_sig:\n{0}".format(pprint_log(dict_sig)))
        # dict_sig.update({'ui':'C'+dict_sig['ui']})
        fb.fil[0]['fxqc'].update(self.ui2dict())
        logger.debug("b = {0}".format(pprint_log(fb.fil[0]['fxqc']['b'])))

        self.process_sig_rx(dict_sig)

# ------------------------------------------------------------------------------
    def update_accu_settings(self):
        """
        Calculate number of extra integer bits needed in the accumulator (bit
        growth) depending on the coefficient area (sum of absolute coefficient
        values) for `cmbW == 'auto'` or depending on the number of coefficients
        for `cmbW == 'full'`. The latter works for arbitrary coefficients but
        requires more bits.

        The new values are written to the fixpoint coefficient dict
        `fb.fil[0]['fxqc']['QA']`.
        """
        try:
            if qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "full":
                A_coeff = int(np.ceil(np.log2(len(fb.fil[0]['fxqc']['b']))))
            elif qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "auto":
                A_coeff = int(np.ceil(np.log2(np.sum(np.abs(fb.fil[0]['ba'][0])))))
        except Exception as e:
            logger.error(e)
            return

        if qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "full" or\
                qget_cmb_box(self.wdg_w_accu.cmbW, data=False) == "auto":
            fb.fil[0]['fxqc']['QA']['WF'] = fb.fil[0]['fxqc']['QI']['WF']\
                + fb.fil[0]['fxqc']['QCB']['WF']
            fb.fil[0]['fxqc']['QA']['WI'] = fb.fil[0]['fxqc']['QI']['WI']\
                + fb.fil[0]['fxqc']['QCB']['WI'] + A_coeff

        # calculate total accumulator word length
        fb.fil[0]['fxqc']['QA']['W'] = fb.fil[0]['fxqc']['QA']['WI']\
            + fb.fil[0]['fxqc']['QA']['WF'] + 1

        # update quantization settings
        fb.fil[0]['fxqc']['QA'].update(self.wdg_q_accu.q_dict)

        self.wdg_w_accu.dict2ui(fb.fil[0]['fxqc']['QA'])

# ------------------------------------------------------------------------------
    def dict2ui(self):
        """
        Update all parts of the UI that need to be updated when specs have been
        changed outside this class, e.g. coefficients and coefficient wordlength.
        This also provides the initial setting for the widgets when the filter has
        been changed.

        This is called from one level above by
        :class:`pyfda.input_widgets.input_fixpoint_specs.Input_Fixpoint_Specs`.
        """
        fxqc_dict = fb.fil[0]['fxqc']
        if 'QA' not in fxqc_dict:
            fxqc_dict.update({'QA': {}})  # no accumulator settings in dict yet
            logger.warning("QA key missing")

        if 'QCB' not in fxqc_dict:
            fxqc_dict.update({'QCB': {}})  # no coefficient settings in dict yet
            logger.warning("QCB key missing")

        self.wdg_w_coeffs.dict2ui(fxqc_dict['QCB'])  # update coefficient wordlength
        self.update_accu_settings()                  # update accumulator settings

# ------------------------------------------------------------------------------
    def ui2dict(self):
        """
        Read out the quantization subwidgets and store their settings in the central
        fixpoint dictionary `fb.fil[0]['fxqc']` using the keys described below.

        Coefficients are quantized with these settings in the subdictionary under
        the key 'b'.

        Additionally, these subdictionaries are returned  to the caller
        (``input_fixpoint_specs``) where they are used to update ``fb.fil[0]['fxqc']``

        Parameters
        ----------

        None

        Returns
        -------
        fxqc_dict : dict

           containing the following keys and values:

        - 'QCB': dictionary with coefficients quantization settings

        - 'QA': dictionary with accumulator quantization settings

        - 'b' : list of coefficients in integer format

        """
        fxqc_dict = fb.fil[0]['fxqc']
        if 'QA' not in fxqc_dict:
            # no accumulator settings in dict yet:
            fxqc_dict.update({'QA': self.wdg_w_accu.q_dict})
            logger.warning("Empty dict 'fxqc['QA]'!")
        else:
            fxqc_dict['QA'].update(self.wdg_w_accu.q_dict)

        if 'QCB' not in fxqc_dict:
            # no coefficient settings in dict yet
            fxqc_dict.update({'QCB': self.wdg_w_coeffs.q_dict})
            logger.warning("Empty dict 'fxqc['QCB]'!")
        else:
            fxqc_dict['QCB'].update(self.wdg_w_coeffs.q_dict)

        fxqc_dict.update({'b': self.wdg_w_coeffs.quant_coeffs(self.wdg_w_coeffs.q_dict,
                                                              fb.fil[0]['ba'][0])})
        return fxqc_dict

# ------------------------------------------------------------------------------
    def construct_fixp_filter(self):
        """
        Construct an instance of the fixpoint filter object using the settings from
        the 'fxqc' quantizer dict
        """
        p = fb.fil[0]['fxqc']
        if not all(np.isfinite(p['b'])):
            logger.error("Coefficients contain non-finite values!")
            return
        if any(np.iscomplex(p['b'])):
            logger.error("Coefficients contain complex values!")
            return

        self.filt = FIR()

# ------------------------------------------------------------------------------
    def to_verilog(self, **kwargs):
        """
        Convert the migen description to Verilog
        """
        return verilog.convert(self.fixp_filter,
                               ios={self.fixp_filter.i, self.fixp_filter.o},
                               **kwargs)

    # ------------------------------------------------------------------------------
    def run_sim(self, stimulus):

        def process():
            input = stimulus
            self.output = []
            for i in input:
                yield self.filt.i.eq(int(i))
                yield Tick()
                self.output.append((yield self.filt.o))

        sim = Simulator(self.filt)

        sim.add_clock(1/48000)
        sim.add_process(process)
        sim.run()

        return self.output

###############################################################################
# A synthesizable nMigen FIR filter.
class FIR(Elaboratable):
    def __init__(self):
        self.p = fb.fil[0]['fxqc']  # parameter dictionary with coefficients etc.
        # ------------- Define I/Os as signed --------------------------------------
        self.i = Signal(signed(self.p['QI']['W']))  # input signal
        self.o = Signal(signed(self.p['QO']['W']))  # output signal
        pass

    # def ports(self):
    #     return [self.i, self.o]

    def elaborate(self, platform) -> Module:
        """
        `platform` normally specifies FPGA platform, not needed here.
        """
        m = Module()  # instantiate a module
        ###
        muls = []    # list for partial products b_i * x_i
        DW = int(np.ceil(np.log2(len(self.p['b']))))  # word growth
        # word format for sum of partial products b_i * x_i
        QP = {'WI': self.p['QI']['WI'] + self.p['QCB']['WI'] + DW,
              'WF': self.p['QI']['WF'] + self.p['QCB']['WF']}
        QP.update({'W': QP['WI'] + QP['WF'] + 1})

        src = self.i  # first register is connected to input signal

        for b in self.p['b']:
            sreg = Signal(signed(self.p['QI']['W']))  # create chain of registers
            m.d.sync += sreg.eq(src)            # with input word length
            src = sreg
            muls.append(int(b)*sreg)

        logger.debug("b = {0}\nW(b) = {1}".format(
            pprint_log(self.p['b']), self.p['QCB']['W']))

        # saturation logic doesn't make much sense with a FIR filter, this is
        # just for demonstration
        sum_full = Signal(signed(QP['W']))
        m.d.sync += sum_full.eq(reduce(add, muls))  # sum of multiplication products

        # rescale from full product format to accumulator format
        sum_accu = Signal(signed(self.p['QA']['W']))
        m.d.comb += sum_accu.eq(requant(m, sum_full, QP, self.p['QA']))

        # rescale from accumulator format to output width
        m.d.comb += self.o.eq(requant(m, sum_accu, self.p['QA'], self.p['QO']))

        return m


# ------------------------------------------------------------------------------
if __name__ == '__main__':
    """ Run widget standalone with 
        `python -m pyfda.fixpoint_widgets.fir_df.fir_df_nmigen_ui` 
    """
    from pyfda.libs.compat import QApplication
    from pyfda import pyfda_rc as rc

    filt = FIR()

    def process():
        # input = stimulus
        output = []
        for i in np.ones(20):
            yield filt.i.eq(int(i))
            yield Tick()
            output.append((yield filt.o))
        print(output)

    sim = Simulator(filt)

    sim.add_clock(1/48000)
    sim.add_process(process)
    sim.run()

    # ------------ test ui ----------------
    app = QApplication(sys.argv)
    app.setStyleSheet(rc.qss_rc)
    mainw = FIR_DF_NM_ui()
    app.setActiveWindow(mainw)
    mainw.show()
    sys.exit(app.exec_())
