#!/usr/bin/env python3
"""
Drift Predictor - predicts final chain fidelity from early-hop drift patterns.

Given the first N hops of a semantic drift chain, predicts:
  - Final fidelity (similarity of endpoint to source)
  - Whether the chain will converge or diverge
  - Estimated total accumulated drift

Method: We fit a simple exponential model to early drift rates:
  drift(t) = A * exp(-lambda*t) + C  (converging)
  drift(t) = A * exp(+lambda*t) + C  (diverging)

The decay/growth rate lambda determines the trajectory.
"""
import math, json
from pathlib import Path

class DriftPredictor:
    """Predicts final chain fidelity from early-hop drift patterns."""
    
    def fit_exponential(self, drifts):
        """Fit exponential model to drift sequence."""
        if len(drifts) < 3:
            return None
        
        increments = [drifts[i] - drifts[i-1] if i > 0 else drifts[i] 
                      for i in range(len(drifts))]
        valid = [(i, inc) for i, inc in enumerate(increments) if inc > 0.001]
        
        if len(valid) < 2:
            return {"A": 0, "lambda": 0, "C": increments[-1] if increments else 0, "type": "converged"}
        
        n = len(valid)
        sum_x = sum(v[0] for v in valid)
        sum_y = sum(math.log(v[1]) for v in valid)
        sum_xy = sum(v[0] * math.log(v[1]) for v in valid)
        sum_x2 = sum(v[0] ** 2 for v in valid)
        
        denom = n * sum_x2 - sum_x ** 2
        if abs(denom) < 1e-10:
            return {"A": increments[0], "lambda": 0, "C": 0, "type": "constant"}
        
        lam = -(n * sum_xy - sum_x * sum_y) / denom
        log_A = (sum_y + lam * sum_x) / n
        A = math.exp(log_A)
        
        drift_type = "converging" if lam > 0 else "diverging"
        C = max(0, increments[-1] - A * math.exp(-lam * len(increments))) if len(increments) > 0 else 0
        
        return {"A": A, "lambda": lam, "C": C, "type": drift_type}
    
    def predict(self, similarities, total_steps=None):
        """Predict final fidelity from observed similarities so far."""
        if len(similarities) < 3:
            return {
                "predicted_fidelity": similarities[-1] if similarities else 1.0,
                "trajectory": "unknown",
                "confidence": 0.0,
                "warning": "Need at least 3 data points"
            }
        
        drifts = [1.0 - s for s in similarities]
        model = self.fit_exponential(drifts)
        if model is None:
            return {"predicted_fidelity": similarities[-1], "trajectory": "unknown", "confidence": 0.0}
        
        current_step = len(drifts) - 1
        predict_to = total_steps if total_steps else current_step + 5
        
        if model["type"] == "converged":
            predicted_final_drift = drifts[-1]
            trajectory = "converged"
        elif model["type"] == "converging":
            predicted_final_drift = drifts[-1] + sum(
                model["A"] * math.exp(-model["lambda"] * (current_step + k))
                for k in range(1, predict_to - current_step + 1)
            )
            predicted_final_drift = min(predicted_final_drift, len(drifts))
            trajectory = "converging"
        elif model["type"] == "diverging":
            predicted_final_drift = drifts[-1] + sum(
                model["A"] * math.exp(model["lambda"] * k)
                for k in range(1, predict_to - current_step + 1)
            )
            predicted_final_drift = min(predicted_final_drift, len(drifts) * 2)
            trajectory = "diverging"
        else:
            predicted_final_drift = drifts[-1]
            trajectory = "constant"
        
        predicted_fidelity = max(0.0, 1.0 - predicted_final_drift)
        confidence = min(1.0, len(similarities) / 8.0)
        
        drift_increments = [drifts[i] - drifts[i-1] for i in range(1, len(drifts))]
        if drift_increments:
            monotonic = sum(1 for i in range(1, len(drift_increments)) 
                          if (drift_increments[i] > 0) == (drift_increments[0] > 0)) / max(1, len(drift_increments) - 1)
            confidence *= (0.5 + 0.5 * monotonic)
        
        return {
            "predicted_fidelity": round(predicted_fidelity, 4),
            "trajectory": trajectory,
            "confidence": round(confidence, 3),
            "model": model,
            "current_fidelity": round(similarities[-1], 4),
            "current_drift": round(drifts[-1], 4),
            "steps_observed": len(similarities),
            "steps_predicted_to": predict_to
        }
    
    def predict_chain(self, similarities_sequence, horizon=5):
        """Predict fidelity at each future step."""
        predictions = []
        for step in range(1, horizon + 1):
            result = self.predict(similarities_sequence, 
                                  total_steps=len(similarities_sequence) + step - 1)
            predictions.append({
                "step": len(similarities_sequence) + step - 1,
                "predicted_fidelity": result["predicted_fidelity"],
                "trajectory": result["trajectory"]
            })
        return predictions

def demo():
    """Demonstrate drift prediction."""
    print("DRIFT PREDICTOR - DEMO")
    print("=" * 72)
    
    predictor = DriftPredictor()
    
    print("\n1. CONVERGING CHAIN (drift decreases over time)")
    converging = [1.0, 0.85, 0.75, 0.70, 0.68, 0.67]
    result = predictor.predict(converging)
    print("   Observed: %s" % [round(s, 3) for s in converging])
    print("   Predicted fidelity: %.4f" % result["predicted_fidelity"])
    print("   Trajectory: %s" % result["trajectory"])
    print("   Confidence: %.3f" % result["confidence"])
    
    forward = predictor.predict_chain(converging, horizon=5)
    print("   Forward: %s" % [round(p["predicted_fidelity"], 3) for p in forward])
    
    print("\n2. DIVERGING CHAIN (drift increases over time)")
    diverging = [1.0, 0.90, 0.72, 0.55, 0.38, 0.22]
    result = predictor.predict(diverging)
    print("   Observed: %s" % [round(s, 3) for s in diverging])
    print("   Predicted fidelity: %.4f" % result["predicted_fidelity"])
    print("   Trajectory: %s" % result["trajectory"])
    print("   Confidence: %.3f" % result["confidence"])
    
    print("\n3. EARLY PREDICTION (3 hops, predict to 8)")
    early = [1.0, 0.88, 0.65]
    result = predictor.predict(early, total_steps=8)
    print("   Observed: %s" % [round(s, 3) for s in early])
    print("   Predicted at step 8: %.4f | Trajectory: %s | Confidence: %.3f" % (
        result["predicted_fidelity"], result["trajectory"], result["confidence"]))
    
    print("\n4. TELEPHONE GAME (LLM drift tracker data)")
    telephone = [1.0, 0.948, 0.945, 1.000, 0.863, 0.832]
    result = predictor.predict(telephone, total_steps=8)
    print("   Observed: %s" % [round(s, 3) for s in telephone])
    print("   Predicted at step 8: %.4f | Trajectory: %s" % (
        result["predicted_fidelity"], result["trajectory"]))
    
    print("\n5. ACCURACY: predict from first 3 hops vs actual")
    partial = telephone[:3]
    result = predictor.predict(partial, total_steps=6)
    actual = telephone[-1]
    error = abs(result["predicted_fidelity"] - actual)
    print("   Predicted: %.4f | Actual: %.4f | Error: %.4f" % (
        result["predicted_fidelity"], actual, error))
    
    print("\n" + "=" * 72)

if __name__ == "__main__":
    demo()
