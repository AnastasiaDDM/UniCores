from app.util.db import db
from app.core.exceptions import *
from datetime import datetime
from decimal import Decimal
from app.util import check
from app.util import config, log
from app.util.util import tz_utcnow


# Система логов сама находит свои конфиги, если они лежат в папке Config
lg = log.getlogger('api')


class UniCore:
    """Класс для общих методов обработки одиногочного экземпляра пользовательских классов"""

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


class UniCores:
    """Класс для общих методов обработки экземпляров пользовательских классов"""

    @staticmethod
    def get_method_by_name(obj_class, name_method):
        """Метод возвращает метод пользователского класса obj_class по имени метода name_method"""
        return obj_class.get_methods()[name_method]["func"]

    @staticmethod
    def add(obj_dict, obj_class, exc, mode_return=None):
        """
        Функция добавления общая. Добавление будет успешным в случае, если такого же объекта
        в бд нет, проверка производится по полю __non_repeat__ из пользовательского класса.

        Args:
            obj_dict (dict): словарь атрибутов объекта и их значений для добавления в бд
            obj_class (class): пользовательский класс экземпляра
            exc (class): пользователский класс ошибки
            mode_return (str): режим возврата данных, "raw_obj" - возращается объект, иначе словарь

        Returns:
            dict: объект в формате JSON (или объект, если mode_return='raw_obj'), иначе Exception
        """

        session = db.session()  # Открывается сессия доступа к бд
        try:
            obj = obj_class()

            if 'id' in obj_dict:  # ID в бд проставляется автоматически
                obj_dict.pop('id', None)
            if 'current_user_id' in obj_dict:  # ID текущего пользователя определяется автоматически
                obj_dict.pop('current_user_id', None)

            # Флаг на успешное дальнейшее выполнение операции (когда такого объекта нет в бд)
            flag_success = True
            # Проверяем есть ли объект с такими данными в бд
            try:
                obj_non_repeat = session.query(obj_class).filter(obj_class.date_del == None)
                non_repeat = obj_class.__non_repeat__  # Получаем атрибуты, которые принято считать
                for key in non_repeat:                 # полным сходством объектов
                    obj_non_repeat = obj_non_repeat.filter(non_repeat[key] == obj_dict[key])

                if obj_non_repeat.first():  # Получаем первый элемент из отфильтрованного запроса
                    flag_success = False
            except:
                pass

            if flag_success:  # Проверка добавляемого объекта на повтор пройдена
                obj.update(obj_dict)  # Передаем словарь данных в метод update в классе UniCore

                session.add(obj)  # Работа с сессией, добавление, коммит
                session.commit()
                lg.info(str(obj_class) + "::" + str(obj.id) + "::Объект успешно добавлен")
                if mode_return == 'raw_obj':
                    return obj
                return obj.get_dict()

            raise ObjectAlreadyExistsEx('Такой объект уже существует')
        except Exception as error:
            session.rollback()  # Откат изменений в бд
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" + str(
                obj_dict.get('id', None)) + "::" + str(exc(str(error))))
            if type(error) == ObjectAlreadyExistsEx:
                raise error
            raise exc(str(error))

    @staticmethod
    def update(obj_dict, obj_class, exc):
        """
        Функция изменения общая. В obj_dict обязательно должен быть ключ "id" для поиска
        изменяемого объекта в бд.

        Args:
            obj_dict (dict): словарь атрибутов объекта и их значений для изменения в бд
            obj_class (class): пользовательский класс экземпляра
            exc (class): пользовательский класс ошибки

        Returns:
            bool: True при успешном изменении, иначе Exception
        """

        session = db.session()
        try:
            if check.isdigit(obj_dict.get('id', None)):  # Проверка id объекта

                obj = session.query(obj_class).get(obj_dict['id'])  # Получение объекта по id
                if obj:
                    if 'current_user_id' in obj_dict:
                        obj_dict.pop('current_user_id', None)
                    obj.update(obj_dict)  # Передаем словарь данных в метод update в классе UniCore
                    session.add(obj)  # Работа с сессией, добавление, коммит
                    session.commit()
                    lg.info(str(obj_class) + "::" + str(obj_dict['id']) +
                            "::Объект успешно изменен")
                    return True
                raise ObjectNotFound(str(obj_dict['id']))
            raise WrongIDEx(str(obj_dict.get('id', None)))
        except Exception as error:
            session.rollback()
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" +
                       str(obj_dict.get('id', None)) + "::" + str(exc(str(error))))
            if type(error) == ObjectNotFound or type(error) == WrongIDEx:
                raise error
            raise exc(str(error))

    @staticmethod
    def get(obj_dict, obj_class, exc, mode_return=None):
        """
        Функция получения объекта общая.

        Args:
           obj_dict (dict): словарь с id объекта (возможно mode(str) - режим поиска данных,
            "all" - ищет среди всех (удаленных и неудаленных), иначе поиск среди только неудаленных
           obj_class (class): пользовательский класс экземпляра
           exc (class): пользовательский класс ошибки
           mode_return (str): режим возврата данных, "raw_obj" возращается объект, иначе словарь

        Returns:
           dict: объект в формате JSON (или объект, если mode_return='raw_obj'), иначе Exception
        """

        session = db.session()
        try:
            # Получение полного названия атрибута ID в пользовательском классе
            id = None
            id = UniCores.get_id_from_obj_dict(obj_dict, obj_class)
            if check.isdigit(id):
                id = int(id)
                obj = None

                mode = ''
                if 'mode' in obj_dict:  # Проверка mode в obj_dict
                    if obj_dict['mode'] == 'all':
                        mode = 'all'

                if mode == 'all':
                    # Получение любого (удаленного, неудаленного) объекта
                    obj = session.query(obj_class).filter(obj_class.id == id).first()
                else:
                    if obj_class().has_attr('date_del'):  # Есть дата удаления у объекта
                        # Получение неудаленного объекта
                        obj = session.query(obj_class).filter(obj_class.id == id,
                                                              obj_class.date_del is None).first()

                if obj:
                    if mode_return == 'raw_obj':
                        return obj
                    return obj.get_dict()
                raise ObjectNotFound(str(id))
            raise WrongIDEx(str(id))
        except Exception as error:
            session.rollback()
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" + str(id) + "::" + str(exc(str(error))))
            if type(error) == ObjectNotFound or type(error) == WrongIDEx:
                raise error
            raise exc(str(error))

    # Получение id из obj_dict
    @staticmethod
    def __get_id_from_obj_dict(obj_dict, obj_class):
        id = None
        # if obj_class in (app.core.clients.models.Client, app.core.staff.models.Staff):
        #     obj_class = User
        # Получаем название ключевого поля, переданного извне
        try:
            name_field_id = obj_class().__name_field_id__
            id = obj_dict[name_field_id]

        except:
            id = obj_dict.get('id', None)
        return id

    # Оболочка для внутренней функции __get_id_from_obj_dict
    @staticmethod
    def get_id_from_obj_dict(obj_dict, obj_class):
        """

            Функция получения id из obj_dict

            Args:
                obj_dict (dict): Словарь параметров
                obj_class (class): Класс экземпляра

            Returns:
                int: ID объекта при успешном выполнении, иначе Exception

        """

        return UniCores.__get_id_from_obj_dict(obj_dict, obj_class)

