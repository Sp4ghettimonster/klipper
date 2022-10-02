#import logging
from . import bus

MLX90614_CHIP_ADDR = 0x48
MLX90614_I2C_SPEED = 100000
MLX90614_REGS = {
    'TEMP'   : 0x07,    
}

# define a new temperature sensor
class MLX90614:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.name = config.get_name().split()[-1]
        self.i2c = bus.MCU_I2C_from_config(config, MLX90614_CHIP_ADDR, MLX90614_I2C_SPEED)
        self.regs = MLX90614_REGS
        self.temp = 0
        self.printer.register_event_handler("klippy:ready", self.handle_ready)
        self.printer.register_event_handler("klippy:shutdown", self.handle_shutdown)
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode.register_mux_command("MLX90614", "TEMP", self.name,
                                        self.cmd_MLX90614_TEMP,
                                        desc=self.cmd_MLX90614_TEMP_help)
    def handle_shutdown(self):
        self.gcode.reset_last_position()
    cmd_MLX90614_TEMP_help = "Get temperature from MLX90614"
    def cmd_MLX90614_TEMP(self, params):
        self.gcode.reset_last_position()
        self.update_temp()
        self.gcode.respond_info("MLX90614_TEMP: %s" % (self.temp))
    def update_temp(self):
        self.i2c.write([self.regs['TEMP']])
        data = self.i2c.read(2)
        self.temp = data[1] + (data[0] << 8)
        self.temp = self.temp * 0.02 - 273.15
    def move_update(self, print_time, move):
        self.update_temp()
    def get_status(self, eventtime):
        return {'Temperature': round(self.temp, 2)}

def load_config(config):
    return MLX90614(config)
