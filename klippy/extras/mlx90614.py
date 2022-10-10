#support for I2C MLX90614 temperature sensor
#
#Copyright (C) 2022 Alexander Romboy
#adapted from LM75 code by Boleslaw Ciesielski

import logging
from . import bus

MLX90614_CHIP_ADDR = 0x5A
MLX90614_I2C_SPEED = 100000
MLX90614_REGS = {
    'TEMP'   : 0x07, 
    'MLX90614_ID1' : 0x3C
}
MLX90614_REPORT_TIME = 0.7
# Temperature can be sampled at any time but the read aborts
# the current conversion. Conversion time is 300ms so make
# sure not to read too often.
MLX90614_MIN_REPORT_TIME = 0.5

# define a new temperature sensor
class MLX90614:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.reactor = self.printer.get_reactor()
        self.i2c = bus.MCU_I2C_from_config(config, MLX90614_CHIP_ADDR, MLX90614_I2C_SPEED)
        self.mcu = self.i2c.get_mcu()
        self.report_time = config.getfloat('mlx90614_report_time', MLX90614_REPORT_TIME,
                                           minval=MLX90614_MIN_REPORT_TIME)
        self.temp = 0
        self.min_temp = 0
        self.max_temp = 1000
        self.sample_timer = self.reactor.register_timer(self._sample_mlx90614)
        self.printer.add_object("mlx90614 %s" % (self.name), self)
        self.printer.register_event_handler("klippy:connect", self.handle_connect)
   
    def handle_connect(self):
        self._init_mlx90614()
        self.reactor.update_timer(self.sample_timer, self.reactor.NOW)

    def setup_minmax(self, min_temp, max_temp):
        self.min_temp = min_temp
        self.max_temp = max_temp
    
    def setup_callback(self, cb): #passt
        self._callback = cb
    
    def get_report_time_delta(self):
        return self.report_time
    
    def kelvin_to_celsius(self, x):
        return (x[1] << 8 | x[0]) * 0.02 - 273.15

    def read_register(self, reg_name, read_len):
        # read a single register
        regs = [MLX90614_REGS[reg_name]]
        params = self.i2c.i2c_read(regs, read_len)
        return bytearray(params['response'])

    def _init_mlx90614(self):
        try:
            prodid = self.read_register('MLX90614_ID1', 1)[0]
            logging.info("MLX90614: PRODID %s" % (prodid))
        except:
            pass

    def _sample_mlx90614(self, eventtime):
        try:
            sample = self.read_register('TEMP', 2)
            self.temp = self.kelvin_to_celsius(sample)
        except Exception:
            logging.exception("MLX90614: Error reading data")
            self.temp = 0.0
            return self.reactor.NEVER

        if self.temp < self.min_temp or self.temp > self.max_temp:
            self.printer.invoke_shutdown(
                "MLX90614 temperature %0.1f outside range of %0.1f:%.01f"
                % (self.temp, self.min_temp, self.max_temp))
        
        measured_time = self.reactor.monotonic()
        self._callback(self.mcu.estimated_print_time(measured_time), self.temp)
        return measured_time + self.report_time
    

    def write_register(self, reg_name, data):
        if type(data) is not list:
            data = [data]
        reg = MLX90614_REGS[reg_name]
        data.insert(0, reg)
        self.i2c.i2c_write(data)

    def get_status(self, eventtime):
        return {'Temperature': round(self.temp, 2)} #passt

def load_config(config):
    pheaters = config.get_printer().load_object(config, "heaters")
    pheaters.add_sensor_factory("MLX90614", MLX90614)
