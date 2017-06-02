import sys
import glob
import time
import textwrap

import numpy  as np
import tables as tb

from .. core.configure         import configure
from .. core.system_of_units_c import units

from .. reco                   import tbl_functions as tbl
from .. reco.dst_io            import kr_writer
from .. reco.pmaps_functions   import load_pmaps
from .. reco.tbl_functions     import get_event_numbers_and_timestamps_from_file_name

from .  base_cities            import City
from .  base_cities            import S12SelectorCity


class Dorothea(City, S12SelectorCity):
    def __init__(self,
                 run_number  = 0,
                 files_in    = None,
                 file_out    = None,
                 compression = "ZLIB4",
                 nprint      = 10000,

                 drift_v     = 1 * units.mm / units.mus,

                 S1_Emin     = 0,
                 S1_Emax     = np.inf,
                 S1_Lmin     = 0,
                 S1_Lmax     = np.inf,
                 S1_Hmin     = 0,
                 S1_Hmax     = np.inf,
                 S1_Ethr     = 0,

                 S2_Nmax     = 1,
                 S2_Emin     = 0,
                 S2_Emax     = np.inf,
                 S2_Lmin     = 0,
                 S2_Lmax     = np.inf,
                 S2_Hmin     = 0,
                 S2_Hmax     = np.inf,
                 S2_NSIPMmin = 1,
                 S2_NSIPMmax = np.inf,
                 S2_Ethr     = 0):

        City       .__init__(self,
                             run_number ,
                             files_in   ,
                             file_out   ,
                             compression,
                             nprint     )

        S12SelectorCity.__init__(self,
                                 drift_v     = drift_v,

                                 S1_Nmin     = 1,
                                 S1_Nmax     = 1,
                                 S1_Emin     = S1_Emin,
                                 S1_Emax     = S1_Emax,
                                 S1_Lmin     = S1_Lmin,
                                 S1_Lmax     = S1_Lmax,
                                 S1_Hmin     = S1_Hmin,
                                 S1_Hmax     = S1_Hmax,
                                 S1_Ethr     = S1_Ethr,

                                 S2_Nmin     = 1,
                                 S2_Nmax     = S2_Nmax,
                                 S2_Emin     = S2_Emin,
                                 S2_Emax     = S2_Emax,
                                 S2_Lmin     = S2_Lmin,
                                 S2_Lmax     = S2_Lmax,
                                 S2_Hmin     = S2_Hmin,
                                 S2_Hmax     = S2_Hmax,
                                 S2_NSIPMmin = S2_NSIPMmin,
                                 S2_NSIPMmax = S2_NSIPMmax,
                                 S2_Ethr     = S2_Ethr)

    def run(self, nmax):
        self.display_IO_info(nmax)
        with tb.open_file(self.output_file, "w",
                          filters = tbl.filters(self.compression)) as h5out:

            write_kr = kr_writer(h5out)

            nevt_in, nevt_out = self._main_loop(write_kr, nmax)
        print(textwrap.dedent("""
                              Number of events in : {}
                              Number of events out: {}
                              Ratio               : {}
                              """.format(nevt_in, nevt_out, nevt_out / nevt_in)))
        return nevt_in, nevt_out

    def _main_loop(self, write_kr, nmax):
        nevt_in = nevt_out = 0
        for filename in self.input_files:
            print("Opening {}".format(filename), end="... ")

            try:
                S1s, S2s, S2Sis = load_pmaps(filename)
            except (ValueError, tb.exceptions.NoSuchNodeError):
                print("Empty file. Skipping.")
                continue

            event_numbers, timestamps = get_event_numbers_and_timestamps_from_file_name(filename)

            nevt_in, nevt_out, max_events_reached = (
             self._event_loop(event_numbers, timestamps, nmax, nevt_in, nevt_out, write_kr, S1s, S2s, S2Sis))

            if max_events_reached:
                print('Max events reached')
                break
            else:
                print("OK")

        return nevt_in, nevt_out

    def _event_loop(self, event_numbers, timestamps, nmax, nevt_in, nevt_out, write_kr, S1s, S2s, S2Sis):
        max_events_reached = False
        for evt_number, evt_time in zip(event_numbers, timestamps):
            nevt_in +=1

            S1 = S1s  .get(evt_number, {})
            S2 = S2s  .get(evt_number, {})
            Si = S2Sis.get(evt_number, {})

            evt = self.select_event(evt_number, evt_time, S1, S2, Si)

            if evt:
                nevt_out += 1
                write_kr(evt)

            if not nevt_in % self.nprint:
                print("{} evts analyzed".format(nevt_in))

            if self.max_events_reached(nmax, nevt_in):
                max_events_reached = True
                break
        return nevt_in, nevt_out, max_events_reached

def DOROTHEA(argv = sys.argv):
    """Dorothea DRIVER"""

    # get parameters dictionary
    CFP = configure(argv)

    #class instance
    dorothea = Dorothea(run_number  = CFP.RUN_NUMBER,
                        files_in    = sorted(glob.glob(CFP.FILE_IN)),
                        file_out    = CFP.FILE_OUT,
                        compression = CFP.COMPRESSION,
                        nprint      = CFP.NPRINT,

                        drift_v     = CFP.DRIFT_V * units.mm/units.mus,

                        S1_Emin     = CFP.S1_EMIN * units.pes,
                        S1_Emax     = CFP.S1_EMAX * units.pes,
                        S1_Lmin     = CFP.S1_LMIN,
                        S1_Lmax     = CFP.S1_LMAX,
                        S1_Hmin     = CFP.S1_HMIN * units.pes,
                        S1_Hmax     = CFP.S1_HMAX * units.pes,
                        S1_Ethr     = CFP.S1_ETHR * units.pes,

                        S2_Nmax     = CFP.S2_NMAX,
                        S2_Emin     = CFP.S2_EMIN * units.pes,
                        S2_Emax     = CFP.S2_EMAX * units.pes,
                        S2_Lmin     = CFP.S2_LMIN,
                        S2_Lmax     = CFP.S2_LMAX,
                        S2_Hmin     = CFP.S2_HMIN * units.pes,
                        S2_Hmax     = CFP.S2_HMAX * units.pes,
                        S2_NSIPMmin = CFP.S2_NSIPMMIN,
                        S2_NSIPMmax = CFP.S2_NSIPMMAX,
                        S2_Ethr     = CFP.S2_ETHR * units.pes)

    t0 = time.time()
    nevts = CFP.NEVENTS if not CFP.RUN_ALL else -1
    nevt_in, nevt_out = dorothea.run(nmax = nevts)
    t1 = time.time()
    dt = t1 - t0

    print("run {} evts in {} s, time/event = {}".format(nevt_in, dt, dt/nevt_in))

    # TODO remove
    # return nevts, nevt_in, nevt_out

if __name__ == "__main__":
    DOROTHEA(sys.argv)
