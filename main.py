"""Sistema Software FJ: clientes, servicios y reservas sin base de datos."""
from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal, InvalidOperation
import logging
from pathlib import Path

logging.basicConfig(filename=Path(__file__).with_name('eventos.log'), level=logging.INFO,
                    format='%(asctime)s | %(levelname)s | %(message)s', encoding='utf-8')

class ErrorSistema(Exception):
    """Error de negocio recuperable."""
class DatosInvalidos(ErrorSistema):
    pass
class ServicioNoDisponible(ErrorSistema):
    pass
class ReservaInvalida(ErrorSistema):
    pass

def dinero(valor):
    """Convierte cantidades a Decimal y encadena errores de conversión."""
    try:
        numero = Decimal(str(valor))
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise DatosInvalidos('El valor monetario no es válido') from exc
    if not numero.is_finite() or numero < 0:
        raise DatosInvalidos('El valor monetario debe ser finito y no negativo')
    return numero

class Entidad(ABC):
    @abstractmethod
    def descripcion(self):
        pass

class Cliente(Entidad):
    def __init__(self, identificacion, nombre, correo):
        if not isinstance(identificacion, str) or not identificacion.strip():
            raise DatosInvalidos('La identificación es obligatoria')
        if not isinstance(nombre, str) or len(nombre.strip()) < 2:
            raise DatosInvalidos('El nombre debe tener al menos dos caracteres')
        if not isinstance(correo, str) or correo.count('@') != 1 or '.' not in correo.split('@')[-1]:
            raise DatosInvalidos('El correo no tiene un formato válido')
        self.__identificacion = identificacion.strip()
        self.__nombre = nombre.strip()
        self.__correo = correo.strip()

    @property
    def identificacion(self):
        return self.__identificacion

    def descripcion(self):
        return f'Cliente: {self.__nombre} ({self.__identificacion})'

class Servicio(Entidad, ABC):
    def __init__(self, codigo, nombre, tarifa, disponible=True):
        if not isinstance(codigo, str) or not codigo.strip():
            raise DatosInvalidos('El código del servicio es obligatorio')
        if not isinstance(nombre, str) or not nombre.strip():
            raise DatosInvalidos('El nombre del servicio es obligatorio')
        if not isinstance(disponible, bool):
            raise DatosInvalidos('La disponibilidad debe ser booleana')
        self.codigo = codigo.strip()
        self.nombre = nombre.strip()
        self.tarifa = dinero(tarifa)
        if self.tarifa <= 0:
            raise DatosInvalidos('La tarifa debe ser mayor que cero')
        self.disponible = disponible

    def validar_parametros(self, duracion):
        if isinstance(duracion, bool) or not isinstance(duracion, int) or duracion <= 0:
            raise DatosInvalidos('La duración debe ser un entero positivo')
        if not self.disponible:
            raise ServicioNoDisponible(f'{self.nombre} no está disponible')

    @abstractmethod
    def calcular_costo(self, duracion):
        pass

    def calcular_total(self, duracion, impuesto=0, descuento=0):
        """Simula sobrecarga con parámetros opcionales."""
        base = self.calcular_costo(duracion)
        impuesto, descuento = dinero(impuesto), dinero(descuento)
        if impuesto > 100 or descuento > 100:
            raise DatosInvalidos('Impuesto y descuento deben estar entre 0 y 100')
        return (base * (1 - descuento / 100) * (1 + impuesto / 100)).quantize(Decimal('0.01'))

class Sala(Servicio):
    def __init__(self, codigo, nombre, tarifa, capacidad, disponible=True):
        super().__init__(codigo, nombre, tarifa, disponible)
        if isinstance(capacidad, bool) or not isinstance(capacidad, int) or capacidad <= 0:
            raise DatosInvalidos('La capacidad de la sala debe ser positiva')
        self.capacidad = capacidad

    def validar_parametros(self, duracion):
        super().validar_parametros(duracion)
        if duracion > 12:
            raise DatosInvalidos('Una sala se reserva por máximo 12 horas')

    def calcular_costo(self, duracion):
        self.validar_parametros(duracion)
        return self.tarifa * duracion

    def descripcion(self):
        return f'Sala {self.nombre}, capacidad {self.capacidad} personas'

class Equipo(Servicio):
    def __init__(self, codigo, nombre, tarifa, categoria, disponible=True):
        super().__init__(codigo, nombre, tarifa, disponible)
        if not isinstance(categoria, str) or not categoria.strip():
            raise DatosInvalidos('La categoría del equipo es obligatoria')
        self.categoria = categoria

    def validar_parametros(self, duracion):
        super().validar_parametros(duracion)
        if duracion > 30:
            raise DatosInvalidos('El equipo se alquila por máximo 30 días')

    def calcular_costo(self, duracion):
        self.validar_parametros(duracion)
        return self.tarifa * duracion

    def descripcion(self):
        return f'Equipo {self.nombre}, categoría {self.categoria}'

class Asesoria(Servicio):
    def __init__(self, codigo, nombre, tarifa, especialidad, disponible=True):
        super().__init__(codigo, nombre, tarifa, disponible)
        if not isinstance(especialidad, str) or not especialidad.strip():
            raise DatosInvalidos('La especialidad es obligatoria')
        self.especialidad = especialidad

    def validar_parametros(self, duracion):
        super().validar_parametros(duracion)
        if duracion > 8:
            raise DatosInvalidos('Una asesoría dura máximo 8 horas')

    def calcular_costo(self, duracion):
        self.validar_parametros(duracion)
        return self.tarifa * duracion

    def descripcion(self):
        return f'Asesoría {self.nombre}, especialidad {self.especialidad}'

class Reserva(Entidad):
    def __init__(self, codigo, cliente, servicio, duracion):
        if not isinstance(cliente, Cliente) or not isinstance(servicio, Servicio):
            raise ReservaInvalida('Se requiere un cliente y un servicio válidos')
        servicio.validar_parametros(duracion)
        self.codigo = codigo
        self.cliente = cliente
        self.servicio = servicio
        self.duracion = duracion
        self.estado = 'PENDIENTE'

    def confirmar(self):
        if self.estado != 'PENDIENTE':
            raise ReservaInvalida('Solo se pueden confirmar reservas pendientes')
        self.servicio.validar_parametros(self.duracion)
        self.estado = 'CONFIRMADA'
        logging.info('Reserva %s confirmada', self.codigo)

    def cancelar(self):
        if self.estado == 'CANCELADA':
            raise ReservaInvalida('La reserva ya está cancelada')
        self.estado = 'CANCELADA'
        logging.info('Reserva %s cancelada', self.codigo)

    def procesar(self, impuesto=0, descuento=0):
        try:
            if self.estado != 'CONFIRMADA':
                raise ReservaInvalida('Debe confirmar la reserva antes de procesarla')
            total = self.servicio.calcular_total(self.duracion, impuesto, descuento)
        except ErrorSistema:
            logging.exception('Error al procesar reserva %s', self.codigo)
            raise
        else:
            logging.info('Reserva %s procesada: %s', self.codigo, total)
            return total
        finally:
            logging.info('Finalizó intento de procesamiento de %s', self.codigo)

    def descripcion(self):
        return f'Reserva {self.codigo}: {self.cliente.descripcion()}, {self.servicio.nombre}, estado {self.estado}'

class Sistema:
    def __init__(self):
        self.clientes = []
        self.servicios = []
        self.reservas = []

    def agregar_cliente(self, cliente):
        if not isinstance(cliente, Cliente):
            raise DatosInvalidos('Objeto cliente inválido')
        if any(c.identificacion == cliente.identificacion for c in self.clientes):
            raise DatosInvalidos('El cliente ya está registrado')
        self.clientes.append(cliente)
        logging.info('Cliente registrado: %s', cliente.identificacion)

    def agregar_servicio(self, servicio):
        if not isinstance(servicio, Servicio):
            raise DatosInvalidos('Objeto servicio inválido')
        if any(s.codigo == servicio.codigo for s in self.servicios):
            raise DatosInvalidos('Código de servicio duplicado')
        self.servicios.append(servicio)
        logging.info('Servicio registrado: %s', servicio.codigo)

    def agregar_reserva(self, reserva):
        if not isinstance(reserva, Reserva):
            raise ReservaInvalida('Objeto reserva inválido')
        if reserva.cliente not in self.clientes or reserva.servicio not in self.servicios:
            raise ReservaInvalida('Cliente y servicio deben estar registrados')
        if any(r.codigo == reserva.codigo for r in self.reservas):
            raise ReservaInvalida('Código de reserva duplicado')
        self.reservas.append(reserva)
        logging.info('Reserva creada: %s', reserva.codigo)

def ejecutar_prueba(numero, titulo, accion):
    print(f'\nPrueba {numero}: {titulo}')
    try:
        resultado = accion()
    except (ErrorSistema, ValueError, TypeError) as error:
        logging.exception('Prueba %s fallida: %s', numero, titulo)
        print(f'ERROR CONTROLADO: {error}')
    else:
        print(f'CORRECTO: {resultado if resultado is not None else "Operación realizada"}')
    finally:
        print('La aplicación continúa funcionando.')

def demostracion():
    sistema = Sistema()
    cliente = Cliente('1001', 'Ana Torres', 'ana@ejemplo.com')
    sala = Sala('S01', 'Sala de reuniones', 50000, 10)
    equipo = Equipo('E01', 'Portátil', 35000, 'Computación')
    asesoria = Asesoria('A01', 'Consultoría Python', 80000, 'Programación')

    operaciones = [
        ('Registrar cliente válido', lambda: sistema.agregar_cliente(cliente)),
        ('Rechazar cliente sin nombre', lambda: Cliente('1002', '', 'a@ejemplo.com')),
        ('Rechazar correo inválido', lambda: Cliente('1003', 'Pedro', 'correo_invalido')),
        ('Rechazar cliente duplicado', lambda: sistema.agregar_cliente(cliente)),
        ('Registrar servicio de sala', lambda: sistema.agregar_servicio(sala)),
        ('Registrar alquiler de equipo', lambda: sistema.agregar_servicio(equipo)),
        ('Registrar servicio de asesoría', lambda: sistema.agregar_servicio(asesoria)),
        ('Rechazar tarifa negativa', lambda: Sala('S02', 'Sala B', -100, 5)),
        ('Rechazar servicio duplicado', lambda: sistema.agregar_servicio(sala)),
        ('Calcular costo con impuesto y descuento', lambda: sala.calcular_total(2, 19, 10)),
        ('Rechazar duración inválida', lambda: Reserva('R00', cliente, sala, -2)),
    ]
    for numero, (titulo, accion) in enumerate(operaciones, 1):
        ejecutar_prueba(numero, titulo, accion)

    reserva = Reserva('R01', cliente, sala, 2)
    ejecutar_prueba(12, 'Crear reserva válida', lambda: sistema.agregar_reserva(reserva))
    ejecutar_prueba(13, 'Procesar reserva sin confirmar', lambda: reserva.procesar())
    ejecutar_prueba(14, 'Confirmar reserva', lambda: reserva.confirmar())
    ejecutar_prueba(15, 'Procesar reserva confirmada', lambda: reserva.procesar(19, 10))
    ejecutar_prueba(16, 'Cancelar reserva', lambda: reserva.cancelar())
    ejecutar_prueba(17, 'Rechazar cancelación repetida', lambda: reserva.cancelar())

    print('\nSIMULACIÓN FINALIZADA. Consulte eventos.log para revisar los registros.')

if __name__ == '__main__':
    print('SOFTWARE FJ - SISTEMA DE CLIENTES, SERVICIOS Y RESERVAS')
    demostracion()