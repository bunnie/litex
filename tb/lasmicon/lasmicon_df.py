from migen.fhdl.std import *
from migen.bus import lasmibus
from migen.actorlib import dma_lasmi
from migen.sim.generic import Simulator, TopLevel, Proxy

from misoclib.lasmicon import *

from common import sdram_phy, sdram_geom, sdram_timing, DFILogger

class TB(Module):
	def __init__(self):
		self.submodules.ctler = LASMIcon(sdram_phy, sdram_geom, sdram_timing)
		# FIXME: remove dummy master
		self.submodules.xbar = lasmibus.Crossbar([self.ctler.lasmic], 2, self.ctler.nrowbits)
		self.submodules.logger = DFILogger(self.ctler.dfi)
		self.submodules.writer = dma_lasmi.Writer(self.xbar.masters[0])

		self.comb += self.writer.address_data.stb.eq(1)
		pl = self.writer.address_data.payload
		pl.a.reset = 255
		pl.d.reset = pl.a.reset*2
		self.sync += If(self.writer.address_data.ack,
			pl.a.eq(pl.a + 1),
			pl.d.eq(pl.d + 2)
		)
		self.open_row = None

	def do_simulation(self, s):
		dfip = Proxy(s, self.ctler.dfi)
		for p in dfip.phases:
			if p.ras_n and not p.cas_n and not p.we_n: # write
				d = dfip.phases[0].wrdata | (dfip.phases[1].wrdata << 64)
				print(d)
				if d != p.address//2 + p.bank*512 + self.open_row*2048:
					print("**** ERROR ****")
			elif not p.ras_n and p.cas_n and p.we_n: # activate
				self.open_row = p.address

def main():
	sim = Simulator(TB(), TopLevel("my.vcd"))
	sim.run(3500)

main()
