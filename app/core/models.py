"""Модуль для общих классов и методов. Ядро для наследования пользовательскими классами."""

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
    __fields_dict__ = None

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
        Функция изменения атрибутов объекта на поля из obj_dict.

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
        Функция мягкого удаления объекта. В бд проставляется параметр удаления, дата или флаг.

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
        Функция установки даты date атрибуту объекта из attr_date.

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
        Функция проверки наличия поля под названием name у текущего объекта.

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
                obj_non_repeat = session.query(obj_class).filter(obj_class.date_del is None)
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
           obj_dict (dict): словарь с двумя возможными ключами id и mode (mode(str) - режим поиска
            данных, "all" - ищет среди всех объектов бд (удаленных и неудаленных),
            иначе поиск среди только неудаленных
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

                if obj_dict.get('mode') == 'all':  # Передан параметр mode для поиска в бд
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
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" + str(id) + "::" +
                       str(exc(str(error))))
            if type(error) == ObjectNotFound or type(error) == WrongIDEx:
                raise error
            raise exc(str(error))

    @staticmethod
    def delete(obj_dict, obj_class, exc, mode=None):
        """
        Функция удаления объекта общая. Реализованы мягкое и жесткое удаление.

        Args:
           obj_dict (dict): словарь с id объекта
           obj_class (class): пользовательский класс экземпляра
           exc (class): пользовательский класс ошибки
           mode (str): режим удаления данных, "remove" - жесткое удаление из бд,
            иначе установка даты удаления

        Returns:
           bool: True при успешном удалении, иначе Exception
        """

        session = db.session()
        try:
            id = UniCores.get_id_from_obj_dict(obj_dict, obj_class)
            # Проверка id объекта
            if check.isdigit(id):
                # Получение объекта
                obj = session.query(obj_class).get(int(id))
                if obj:
                    if mode == 'remove':
                        # Удаление объекта из бд
                        UniCores.delete_hard(obj, obj_class, exc)
                    else:
                        obj.delete()
                        session.commit()
                    lg.info(str(obj_class) + "::" + str(obj.id) + "::Объект успешно удален")
                    return True
                raise ObjectNotFound(str(id))
            raise WrongIDEx(str(id))
        except Exception as error:
            session.rollback()
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" + str(id) + "::" +
                       str(exc(str(error))))
            if type(error) == ObjectNotFound or type(error) == WrongIDEx:
                raise error
            raise exc(str(error))

    # Удаление объекта безусловное
    @staticmethod
    def delete_hard(obj, obj_class, exc):
        """
        Функция "безвозвратного" удаления объекта общая. Жесткое удаление записи из бд.

        Args:
           obj (object): объект
           obj_class (class): пользовательский класс экземпляра
           exc (class): пользовательский класс ошибки

        Returns:
           bool: True при успешном удалении, иначе Exception
        """

        session = db.session()
        try:
            # Проверка наличия объекта
            if obj:
                session.delete(obj)  # Удаление объекта из бд
                session.commit()
                return True
            raise ObjectNotFound(str(obj.id))
        except Exception as error:
            session.rollback()
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" + str(obj.id) +
                       "::" + str(exc(str(error))))
            if type(error) == ObjectNotFound:
                raise error
            raise exc(str(error))

    @staticmethod
    def set_date(obj_dict, attr_date, obj_class, exc, date=None, return_obj=False):
        """
        Функция установки даты в бд общая. Используется для установки даты блокировки и прочего.

        Args:
            obj_dict (dict): словарь, который содержит обязательный параметр - ключ "id"
            attr_date (string): наименование поля даты, например, "date_lock"
            obj_class (class): пользовательский класс экземпляра
            exc (class): пользовательский класс ошибки
            date (datetime): дата для установки
            return_obj (bool): True - вернуть объект в виде словаря, иначе не возвращать

        Returns:
            bool/dict: объект в формате True/JSON при успешном выполнении, иначе Exception
        """

        id = None
        session = db.session()
        try:
            id = UniCores.get_id_from_obj_dict(obj_dict, obj_class)
            if check.isdigit(id):  # Проверка id объекта
                obj = session.query(obj_class).get(int(id))  # Получение объекта
                if obj:
                    obj.set_date(attr_date, date)  # Установка даты в атрибуты объекта
                    session.commit()
                    lg.info(str(obj_class) + "::" + str(obj.id) + "::Объект успешно изменен")

                    if return_obj:  # Нужно передать словарь объекта
                        return obj.get_dict()
                    return True
                raise ObjectNotFound(str(id))
            raise WrongIDEx(str(id))
        except Exception as error:
            session.rollback()
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" + str(id) +
                       "::" + str(exc(str(error))))
            if type(error) == ObjectNotFound or type(error) == WrongIDEx:
                raise error
            raise exc(str(error))

    @staticmethod
    def set_unset(obj_dict, attr_array, obj_class, exc):
        """
        Функция установки связей в промежуточных таблицах общая. Добавление/удаление записей
        из промежуточных таблиц.

        Args:
            obj_dict (dict): словарь параметров для установки, содержит ключи "mode" и
             поля id объектов, со связью которых необходимо работать
            attr_array (array): массив атрибутов целевого класса, которым необходимо установить
             значения из obj_dict
            obj_class (class): пользовательский класс экземпляра
            exc (class): пользовательский класс ошибки

        Returns:
            bool: True при успешном выполнении, иначе Exception
        """

        session = db.session()
        try:
            mode = obj_dict.get('mode')  # Сохранение значения mode
            del (obj_dict['mode'])  # Удаление mode для поиска объекта в бд

            # Получение объекта для удаления или сравнения при добавлении
            query = session.query(obj_class)  # Запрос всех объектов класса obj_class
            for attr in attr_array:
                # Наращивание запроса с фильтрами по полям для связки
                query = query.filter(attr == int(obj_dict.get(str(attr.key))))
            # Сохранение в переменную полученного объекта
            obj = query.first()

            # Проверка mode
            if mode and mode is True:  # Необходимо добавить

                if obj:  # Объект есть, не добавляем
                    raise ObjectAlreadyExistsEx(str(obj_dict))
                else:  # Объекта нет, можно добавлять новый
                    n = obj_class().update(obj_dict)  # Устанвока значений объекту
                    session.add(n)
                    session.commit()
                    lg.info(str(obj_class) + "::" + str(obj_dict) + "::Объект успешно добавлен")
                    return True

            elif mode is False:  # Необходимо удалить
                if obj:  # Объект есть, его можно удалить
                    session.delete(obj)
                    session.commit()
                    lg.info(str(obj_class) + "::" + str(obj_dict) + "::Объект успешно удален")
                    return True
                raise ObjectNotFound(str(obj_dict))
        except Exception as error:
            session.rollback()
            lg.warning(str(type(error)) + "::" + str(obj_class) + "::" + str(obj_dict) +
                       "::" + str(exc(str(error))))
            if type(error) == ObjectNotFound or type(error) == ObjectAlreadyExistsEx:
                raise error
            raise exc(str(error))

    @staticmethod
    def __get_id_from_obj_dict(obj_dict, obj_class):
        """Получение id пользователского объекта из obj_dict"""
        id = None
        try:
            # Получаем название ключевого поля, переданного изпользовательского класса
            name_field_id = obj_class().__name_field_id__
            id = obj_dict[name_field_id]
        except:
            id = obj_dict.get('id', None)
        return id

    @staticmethod
    def get_id_from_obj_dict(obj_dict, obj_class):
        """
        Оболочка для внутренней функции __get_id_from_obj_dict. Функция получения id из obj_dict.
        Необходимо найти id объекта, id может быть задан как "id" или как id конкретного
        пользовательского класса, например, "rate_id".

        Args:
            obj_dict (dict): Словарь параметров для объекта, содержащий поле с id
            obj_class (class): Пользовательский класс экземпляра

        Returns:
            int: ID объекта при успешном выполнении, иначе Exception
        """

        return UniCores.__get_id_from_obj_dict(obj_dict, obj_class)
