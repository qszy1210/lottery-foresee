from fastapi import FastAPI

from .routers import health, predict, stats, data, algorithm, schedule


def create_app() -> FastAPI:
    app = FastAPI(title="Lottery Predictor", version="0.1.0")

    app.include_router(health.router, prefix="/health", tags=["health"])
    app.include_router(predict.router, tags=["predict"])
    app.include_router(stats.router, tags=["stats"])
    app.include_router(data.router, tags=["data"])
    app.include_router(algorithm.router, tags=["algorithm"])
    app.include_router(schedule.router, tags=["schedule"])

    return app


app = create_app()

