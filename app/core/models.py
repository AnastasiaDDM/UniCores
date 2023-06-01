from app.core.exceptions import *
from datetime import datetime
from decimal import Decimal
from app.util import config, log
from app.util.util import tz_utcnow


# Система логов сама находит свои конфиги, если они лежат в папке Config
lg = log.getlogger('api')


class UniCore:
    """Класс для общих методов обработки экземпляров пользовательских классов"""

    def check_obj(self, obj_dict):
        """
        Функция сравнения типов переданных полей в obj_dict и типов полей объекта.
        Применяется для того, чтобы гарантировать правильное соответствие типов
        полей, добавляемых в бд.

        Args:
            obj_dict (dict): словарь полей объекта

        Returns:
            bool: True при соответсвии всех полей указанным типам и
            параметру обязательного поля, иначе False
        """

        try:
            for attr in obj_dict.keys():  # Проверяем на типы и лишние поля
                if attr not in self.__fields_dict__:  # Передан атрибут, которого
                    return False                      # нет в списке полей объекта
                if type(obj_dict[attr]) != self.__fields_dict__[attr]['type']:
                    return False

            for attr in self.__fields_dict__.keys():  # Проверяем на обязательные поля
                if ("nullable" in self.__fields_dict__[attr]
                        and not self.__fields_dict__[attr]['nullable']):

                    if attr not in obj_dict:  # Обязательный атрибут не передан в obj_dict
                        return False
                    if obj_dict[attr] is None:  # Обязательный атрибут не передан в obj_dict
                        return False
            return True  # Данные в obj_dict соответствуют требованиям типа и обязательности
        except Exception as error:
            raise UniCoreSomeEx(str(error))

    def get_dict(self):
        """
        Функция получения словаря dict из атрибутов объекта.

        Returns:
            dict: словарь атрибутов объекта
        """

        d = {}
        for attr in self.__fields_dict__.keys():  # Цикл по всем атрибутам объекта в __fields_dict__
            val = self.__getattribute__(attr)  # Извлекаем значение атрибута конкретного объекта
            if type(val) == float or type(val) == int:  # Атрибут числового типа
                d[attr] = val
            elif isinstance(val, dict) or isinstance(val, list):  # Атрибут составного типа
                d[attr] = val
            elif isinstance(val, Decimal):  # Атрибут числового типа Decimal конвертируется в float
                d[attr] = float(str(val))
            elif val is None:  # Атрибут имеет значение None
                d[attr] = None
            else:
                d[attr] = str(val)
        return d

    def update(self, obj_dict):
        """
        Функция изменения атрибутов объекта на поля из obj_dict

        Args:
            obj_dict (dict): словарь изменяемых полей объекта с новыми значениями

        Returns:
            object: объект, иначе Exception
        """

        if self.check_obj(obj_dict):  # Проверка валидности передаваемых данных
            for attr in obj_dict.keys():
                self.__setattr__(attr, obj_dict[attr])  # Установка значений полям объекта
            if 'date_edit' in self.__dict__:
                self.date_edit = datetime.utcnow()  # При наличии даты изменения устанавливаем ее
        else:
            raise UniCoreUpdateEx("Неверный формат данных при работе с полями объекта")
        return self

    def delete(self):
        """
        Функция удаления объекта.

        Returns:
            object: объект, иначе Exception
        """

        try:
            # Сет всевозможных атрибутов объекта в бд и необходимых значений
            set_attr = {"date_del": tz_utcnow(), "is_delete": True}

            for attr in set_attr.keys():
                # Если такой атрибут у объекта есть, то назначем ему необходимое значение из сета
                if self.has_attr(attr):
                    # Устанавливаем только тогда, когда значение не установлено
                    if self.__getattribute__(attr) is None:
                        # Установка значений полям объекта
                        self.__setattr__(attr, set_attr.get(attr))
        except Exception as error:
            raise UniCoreDelEx(str(error))
        return self

    def set_date(self, attr_date, date=None):
        """
        Функция установки даты date атрибуту объекта из attr_date

        Args:
            attr_date (str): наименование атрибута, где необходимо проставить дату
            date (datetime): дата для обновления значения поля attr_date

        Returns:
            object: объект, иначе Exception
        """

        try:
            if date:  # Конкретная дата передана
                self.__setattr__(attr_date, date)
            else:  # Дата проставляется текущая
                self.__setattr__(attr_date, datetime.utcnow())
        except Exception as error:
            raise UniCoreSomeEx(str(error))
        return self

    def has_attr(self, name):
        """
        Функция проверки наличия поля под названием name у текущего объекта

        Args:
            name (str): искомое название атрибута

        Returns:
            bool: True при наличии, иначе False
        """

        try:
            self.__fields_dict__[name]
            return True
        except Exception:
            return False
