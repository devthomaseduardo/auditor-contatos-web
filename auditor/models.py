from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from auditor.database import Base


def agora_utc():
    return datetime.now(timezone.utc)


class Site(Base):
    __tablename__ = "sites"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    dominio: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        unique=True,
    )

    url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=agora_utc,
    )

    varreduras = relationship(
        "Varredura",
        back_populates="site",
    )


class Varredura(Base):
    __tablename__ = "varreduras"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    site_id: Mapped[int] = mapped_column(
        ForeignKey("sites.id"),
        nullable=False,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="em_andamento",
    )

    quantidade_paginas: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    quantidade_contatos: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    inicio: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=agora_utc,
    )

    fim: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    erro: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    site = relationship(
        "Site",
        back_populates="varreduras",
    )

    contatos = relationship(
        "Contato",
        back_populates="varredura",
    )


class Contato(Base):
    __tablename__ = "contatos"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
    )

    varredura_id: Mapped[int] = mapped_column(
        ForeignKey("varreduras.id"),
        nullable=False,
    )

    email: Mapped[str] = mapped_column(
        String(320),
        nullable=False,
    )

    pagina_origem: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=agora_utc,
    )

    varredura = relationship(
        "Varredura",
        back_populates="contatos",
    )
