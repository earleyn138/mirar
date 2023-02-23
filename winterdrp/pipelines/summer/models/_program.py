"""
Models for the 'program' table
"""
from typing import ClassVar

from pydantic import BaseModel, Field, validator
from sqlalchemy import CHAR, DATE, REAL, VARCHAR, Column, Integer

from winterdrp.pipelines.summer.models.basemodel import Base, BaseDB


class ProgramTable(Base):  # pylint: disable=too-few-public-methods
    """
    Program table in database
    """

    __tablename__ = "program"

    id = Column(Integer, primary_key=True)
    progname = Column(CHAR(8), unique=True)
    prog_key = Column(VARCHAR(50))
    progid = Column(Integer)
    progtitle = Column(VARCHAR(20))
    piname = Column(VARCHAR(20))
    startdate = Column(DATE)
    enddate = Column(DATE)
    hours_allocated = Column(REAL)
    hours_remaining = Column(REAL)
    basepriority = Column(REAL)


class ProgramCredentials(BaseModel):
    """
    Program credentials to access a program
    """

    progname: str = Field(min_length=8, max_length=8, example="2020A000")
    prog_key: str = Field(min_length=1)


class Program(BaseDB, ProgramCredentials):
    """
    A pydantic model for a program database entry
    """

    sql_model: ClassVar = ProgramTable
    progid: int = Field()
    progtitle: str = Field(min_length=1)
    piname: str = Field(min_length=1)
    startdate: str = Field(max_length=10, min_length=10, example="2020-01-01")
    enddate: str = Field(max_length=10, min_length=10, example="2020-01-01")
    hours_allocated: float = Field(ge=0.0)
    hours_remaining: float = Field(ge=0.0)
    basepriority: float = Field(ge=0.0, example=100.0)

    @validator("startdate", "enddate")
    def check_date(cls, value):
        """
        Ensure dates are correctly formatted

        :param value: value
        :return: value
        """
        split = value.split("-")
        assert len(split) == 3
        assert len(split[0]) == 4
        assert len(split[1]) == 2
        assert len(split[2]) == 2
        return value

    @validator("hours_remaining")
    @classmethod
    def validate_time_allocation(cls, field_value, values):
        """
        Ensure that time remaining has a sensible value

        :param field_value: field value
        :param values: values
        :return: field value
        """
        total_time = values["hours_allocated"]
        assert not field_value > total_time
        assert field_value > 0.0
        return field_value
