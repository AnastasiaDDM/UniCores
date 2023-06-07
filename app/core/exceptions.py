"""Пользовательские классы ошибок"""


class CoreEx(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, message):
        self.message = message

    # Переопредление стандартного метода для того, чтобы в текст попадала не только ошибка,
    # но и описание этой ошибки в унаследованных методах.
    def __str__(self):
        return self.message

    def name(self):
        return self.__class__


# # # # # # # # # # UniCore # # # # # # # # # # #
class UniCoreUpdateEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка изменения: " + message


class UniCoreDelEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка удаления: " + message


class UniCoreGetEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка получения: " + message


class UniCoreGetAllEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка получения списка: " + message


class UniCoreSomeEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка некоторого действия: " + message


# # # # # # # # # # Common # # # # # # # # # # #
class ObjectNotFound(CoreEx):

    def __init__(self, message):
        self.message = message


class ObjectAlreadyExistsEx(CoreEx):

    def __init__(self, message):
        self.message = message


class WrongIDEx(CoreEx):

    def __init__(self, message):
        self.message = message


class WrongDataEx(CoreEx):

    def __init__(self, message):
        self.message = message


class GetMethodsEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка получения метода: " + message


class IdempotentOperationsAddEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка добавления идемпотентной операции: " + message


class IdempotentOperationsUpdateEx(CoreEx):

    def __init__(self, message):
        self.message = "Ошибка изменения идемпотентной операции: " + message
