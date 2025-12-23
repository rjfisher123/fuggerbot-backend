"""
Simulation and Strategy Optimization API.

Exposes the 'War Games' simulator and 'Strategy Optimizer' agent to the frontend.
"""
from fastapi import APIRouter, BackgroundTasks, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import logging
import json
import os

from daemon.simulator.war_games_runner import WarGamesRunner
from agents.trm.strategy_optimizer_agent import StrategyOptimizerAgent
from daemon.job_queue import create_job, update_job, get_job, JobStatus, Job, clear_jobs

logger = logging.getLogger("api.simulation")

router = APIRouter(prefix="/api/simulation", tags=["simulation"])
optimizer_router = APIRouter(prefix="/api/optimizer", tags=["optimizer"])

class RunResponse(BaseModel):
    message: str
    job_id: str

async def run_simulation_job(job_id: str):
    """Background task wrapper for simulation."""
    try:
        update_job(job_id, status=JobStatus.RUNNING, progress=10, message="Initializing War Games...")
        
        runner = WarGamesRunner()
        
        def progress_cb(pct, msg):
            update_job(job_id, progress=pct, message=msg)
            
        # Run with callback
        runner.run_all_scenarios(progress_callback=progress_cb)
        
        # Load results to return in job
        results = []
        try:
            with open("data/war_games_results.json", 'r') as f:
                results = json.load(f)
        except:
            pass
            
        update_job(
            job_id, 
            status=JobStatus.COMPLETED, 
            progress=100, 
            message="Simulations Complete",
            result={"scenarios_run": len(results)}
        )
        
    except Exception as e:
        logger.error(f"Simulation job failed: {e}")
        update_job(job_id, status=JobStatus.FAILED, message=str(e))

async def run_optimizer_job(job_id: str):
    """Background task wrapper for optimizer."""
    try:
        update_job(job_id, status=JobStatus.RUNNING, progress=10, message="Initializing Optimizer...")
        
        optimizer = StrategyOptimizerAgent()
        update_job(job_id, progress=50, message="Optimizing Parameters...")
        
        optimizer.optimize()
        
        update_job(job_id, status=JobStatus.COMPLETED, progress=100, message="Optimization Complete")
        
    except Exception as e:
        logger.error(f"Optimizer job failed: {e}")
        update_job(job_id, status=JobStatus.FAILED, message=str(e))

@router.post("/run", response_model=RunResponse)
async def run_simulation(background_tasks: BackgroundTasks):
    """Run War Games simulation (Async Job)."""
    job_id = create_job("simulation")
    background_tasks.add_task(run_simulation_job, job_id)
    return {"message": "Simulation started", "job_id": job_id}

@router.get("/results")
async def get_simulation_results():
    """Get latest simulation results."""
    try:
        if os.path.exists("data/war_games_results.json"):
            with open("data/war_games_results.json", "r") as f:
                return json.load(f)
        return []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status/{job_id}", response_model=Job)
async def get_simulation_job_status(job_id: str):
    """Get status of a specific job."""
    job = get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

@router.post("/reset")
async def reset_simulation():
    """Reset simulation state and clear jobs."""
    clear_jobs()
    logger.info("Simulation jobs cleared via API/reset")
    return {"message": "Simulation reset successfully"}

@optimizer_router.post("/run", response_model=RunResponse)
async def run_optimizer(background_tasks: BackgroundTasks):
    """Run Strategy Optimizer (Async Job)."""
    job_id = create_job("optimizer")
    background_tasks.add_task(run_optimizer_job, job_id)
    return {"message": "Optimizer started", "job_id": job_id}

@optimizer_router.get("/results")
async def get_optimizer_results():
    """
    Get the latest optimized parameters from 'data/optimized_params.json'.
    """
    try:
        if os.path.exists("data/optimized_params.json"):
            with open("data/optimized_params.json", "r") as f:
                return json.load(f)
        return {}
    except Exception as e:
        logger.error(f"Error reading optimized params: {e}")
        return {}
