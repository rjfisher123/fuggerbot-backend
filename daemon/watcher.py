"""
Macro Regime Watcher Daemon.

Main loop that polls for updates and updates the RegimeTracker.
Continuously monitors market signals and detects regime shifts.
"""
import time
import logging
from typing import Optional

from daemon.signal_extractor import SignalExtractor
from daemon.classifier import RegimeClassifier
from context.tracker import RegimeTracker
from context.schemas import MacroRegime

logger = logging.getLogger(__name__)


class MacroDaemon:
    """
    Main daemon that continuously monitors macroeconomic signals
    and updates the regime tracker when shifts are detected.
    
    Runs in a loop, checking for regime changes every 10 minutes.
    """
    
    def __init__(self):
        """Initialize the macro daemon with extractor, classifier, and tracker."""
        logger.info("Initializing MacroDaemon...")
        
        self.extractor = SignalExtractor()
        self.classifier = RegimeClassifier()
        self.tracker = RegimeTracker()
        
        logger.info("✅ MacroDaemon initialized")
        logger.info(f"   Current regime: {self.tracker.get_current_regime().id}")
    
    def run_cycle(self) -> None:
        """
        Run a single cycle of regime detection.
        
        Steps:
        1. Extract hard data (FRED) and soft data (RSS)
        2. Classify current regime using LLM
        3. Compare to current regime in tracker
        4. Update tracker if regime shift detected (and confidence > 0.8)
        """
        try:
            logger.info("=" * 60)
            logger.info("🔄 Running macro regime check cycle...")
            logger.info("=" * 60)
            
            # Step 1: Extract signals
            logger.info("📊 Extracting signals...")
            try:
                all_signals = self.extractor.get_all_signals()
                hard_data = all_signals.get("hard_data", {})
                headlines = all_signals.get("soft_data", [])
                
                logger.info(f"   Hard data series: {len(hard_data)}")
                logger.info(f"   Headlines: {len(headlines)}")
            except Exception as e:
                logger.error(f"❌ Error extracting signals: {e}")
                logger.info("Macro Check: Failed to extract signals")
                return
            
            # Step 2: Classify regime
            logger.info("🤖 Classifying regime...")
            new_regime: Optional[MacroRegime] = None
            try:
                new_regime = self.classifier.analyze_snapshot(hard_data, headlines)
            except Exception as e:
                logger.error(f"❌ Error classifying regime: {e}")
                logger.info("Macro Check: Failed to classify regime")
                return
            
            if new_regime is None:
                logger.warning("⚠️  Classifier returned None, skipping update")
                logger.info("Macro Check: Classification failed")
                return
            
            # Step 3: Compare with current regime
            current_regime = self.tracker.get_current_regime()
            
            # Extract confidence from regime ID (format: REGIME_TYPE_CONFIDENCE)
            # The classifier creates IDs like "INFLATIONARY_80" where 80 = 0.80 confidence
            confidence = 0.5  # Default confidence
            try:
                # Try to extract confidence from ID (last part after underscore)
                parts = new_regime.id.split('_')
                if len(parts) > 1:
                    confidence_str = parts[-1]
                    # Check if it's a number (confidence percentage)
                    if confidence_str.isdigit():
                        confidence = float(confidence_str) / 100.0
                    else:
                        # If not a number, use vibe_score as proxy
                        confidence = new_regime.vibe_score
                else:
                    confidence = new_regime.vibe_score
            except (ValueError, IndexError, AttributeError):
                # Fallback to vibe_score if parsing fails
                confidence = new_regime.vibe_score
                logger.debug(f"Could not parse confidence from ID '{new_regime.id}', using vibe_score: {confidence}")
            
            # Check if regime is different
            is_different = (
                new_regime.id != current_regime.id or
                new_regime.risk_on != current_regime.risk_on or
                abs(new_regime.vibe_score - current_regime.vibe_score) > 0.2
            )
            
            # Step 4: Update if different AND confidence > 0.8
            if is_different and confidence > 0.8:
                logger.info("🚨 REGIME SHIFT DETECTED")
                logger.info(f"   From: {current_regime.id} ({current_regime.name})")
                logger.info(f"   To: {new_regime.id} ({new_regime.name})")
                logger.info(f"   Confidence: {confidence:.2f}")
                logger.info(f"   Risk Mode: {'RISK-ON' if new_regime.risk_on else 'RISK-OFF'}")
                logger.info(f"   Vibe Score: {new_regime.vibe_score:.2f}")
                
                self.tracker.update_regime(new_regime)
                logger.info("✅ Regime tracker updated")
                
            elif is_different:
                logger.info("⚠️  Regime change detected but confidence too low")
                logger.info(f"   New: {new_regime.id} (confidence: {confidence:.2f}, threshold: 0.8)")
                logger.info(f"   Current: {current_regime.id}")
                logger.info("Macro Check: Change detected but below confidence threshold")
                
            else:
                logger.info("✅ No regime change detected")
                logger.info(f"   Current: {current_regime.id} ({current_regime.name})")
                logger.info(f"   Classified: {new_regime.id} (confidence: {confidence:.2f})")
                logger.info("Macro Check: No Change")
            
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"❌ Error in run_cycle: {e}", exc_info=True)
            logger.info("Macro Check: Error in cycle")
    
    def start(self) -> None:
        """
        Start the daemon loop.
        
        Runs continuously, checking for regime changes every 10 minutes (600 seconds).
        """
        logger.info("=" * 60)
        logger.info("🚀 Starting MacroDaemon")
        logger.info("=" * 60)
        logger.info(f"Current regime: {self.tracker.get_current_regime().id}")
        logger.info("Polling interval: 600 seconds (10 minutes)")
        logger.info("Press Ctrl+C to stop")
        logger.info("=" * 60)
        
        cycle_count = 0
        
        try:
            while True:
                cycle_count += 1
                logger.info(f"\n📅 Cycle #{cycle_count} - {time.strftime('%Y-%m-%d %H:%M:%S')}")
                
                self.run_cycle()
                
                logger.info(f"⏸️  Waiting 600 seconds before next cycle...")
                time.sleep(600)  # 10 minutes
                
        except KeyboardInterrupt:
            logger.info("\n" + "=" * 60)
            logger.info("🛑 MacroDaemon stopped by user")
            logger.info(f"Total cycles completed: {cycle_count}")
            logger.info("=" * 60)
        except Exception as e:
            logger.error(f"❌ Fatal error in daemon loop: {e}", exc_info=True)
            raise
    
    def run_once(self) -> None:
        """
        Run a single cycle (useful for testing or manual execution).
        
        Does not start the continuous loop.
        """
        logger.info("Running single macro regime check...")
        self.run_cycle()

