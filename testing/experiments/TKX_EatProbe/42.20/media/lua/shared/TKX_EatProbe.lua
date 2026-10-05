-- TKX_EatProbe -- X45b state table. Shared so lua.global reads it on either side.
-- outermost: true when ISEatFoodAction.complete is still this probe's own wrapper at the first
-- OnTick (the probe loaded last and wraps any earlier wrap, e.g. QualityCooking's); nil until read.
TKX_EatProbe = { version = 1, enter = 0, exit = 0, outermost = nil }
