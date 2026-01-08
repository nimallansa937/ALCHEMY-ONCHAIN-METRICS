"""
Slack notification integration for HIMARI strategic alerts.

Sends alerts for:
- Regime changes
- Parameter adjustment proposals
- Protocol health warnings
- System errors
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests

from .config import SLACK_WEBHOOK_URL, AUTO_APPLY_THRESHOLD

logger = logging.getLogger(__name__)


def send_strategic_alert(
    message: str, 
    severity: str = 'INFO',
    webhook_url: Optional[str] = None
) -> bool:
    """
    Send alert to Slack channel for operator review.
    
    Args:
        message: Alert text (supports Slack markdown)
        severity: INFO, WARNING, or CRITICAL
        webhook_url: Override default webhook URL
        
    Returns:
        True if alert was sent successfully
    """
    url = webhook_url or SLACK_WEBHOOK_URL
    
    if not url:
        logger.warning("No Slack webhook URL configured, alert not sent")
        return False
    
    color_map = {
        'INFO': '#36a64f',      # Green
        'WARNING': '#ff9900',   # Orange
        'CRITICAL': '#ff0000'   # Red
    }
    
    payload = {
        'attachments': [{
            'color': color_map.get(severity, '#808080'),
            'title': f'{severity}: HIMARI Strategic Update',
            'text': message,
            'footer': f'Dune Analytics Pipeline | {datetime.utcnow().strftime("%Y-%m-%d %H:%M UTC")}',
            'mrkdwn_in': ['text']
        }]
    }
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        response.raise_for_status()
        logger.info(f"Sent {severity} alert to Slack")
        return True
    except requests.RequestException as e:
        logger.error(f"Failed to send Slack alert: {e}")
        return False


def propose_parameter_change(
    new_regime: str,
    current_params: Dict[str, Any],
    recommended_params: Dict[str, Any],
    apply_callback=None
) -> bool:
    """
    Propose parameter changes to operator via Slack.
    
    Auto-applies if change is minor (<10%), requires approval if major.
    
    Args:
        new_regime: The new detected regime
        current_params: Current parameter values
        recommended_params: New recommended values
        apply_callback: Function to call to apply params (optional)
        
    Returns:
        True if notification sent successfully
    """
    current_size = current_params.get('max_position_size_btc', 0.5)
    new_size = recommended_params.get('max_position_size_btc', 0.5)
    
    if current_size > 0:
        position_size_change_pct = abs(new_size - current_size) / current_size * 100
    else:
        position_size_change_pct = 100
    
    old_regime = current_params.get('regime', 'UNKNOWN')
    
    message = f"""*Regime Change Detected: {old_regime} → {new_regime}*

*Recommended Parameter Adjustments:*
• Max Position Size: {current_size:.2f} BTC → {new_size:.2f} BTC ({position_size_change_pct:+.1f}%)
• Leverage Limit: {current_params.get('leverage_limit', 2.0):.1f}x → {recommended_params.get('leverage_limit', 2.0):.1f}x
• Risk Budget Multiplier: {current_params.get('risk_budget_multiplier', 1.0):.2f} → {recommended_params.get('risk_budget_multiplier', 1.0):.2f}

*Justification:*
{recommended_params.get('reasoning', 'Regime shift warrants risk adjustment')}
"""
    
    if position_size_change_pct < AUTO_APPLY_THRESHOLD:
        # Auto-apply minor changes
        message += f"\n✅ *Auto-applied* (change < {AUTO_APPLY_THRESHOLD}%)"
        severity = 'INFO'
        
        if apply_callback:
            apply_callback(recommended_params, approved_by='AUTO')
    else:
        # Require manual approval
        message += f"\n⚠️  *Manual approval required* (change >= {AUTO_APPLY_THRESHOLD}%)"
        message += "\nReply `/approve-strategy` to apply"
        severity = 'WARNING'
    
    return send_strategic_alert(message, severity)


def send_regime_change_alert(
    old_regime: str,
    new_regime: str,
    metrics: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Send alert specifically for regime change.
    
    Args:
        old_regime: Previous regime
        new_regime: New detected regime
        metrics: Optional metrics that triggered the change
    """
    message = f"*Market Regime Changed*\n\n{old_regime} → *{new_regime}*"
    
    if metrics:
        message += "\n\n*Key Metrics:*"
        if 'oi_growth_pct_7d' in metrics:
            message += f"\n• OI Growth (7d): {metrics['oi_growth_pct_7d']:.1f}%"
        if 'avg_funding' in metrics:
            message += f"\n• Avg Funding: {metrics['avg_funding']:.4f}"
        if 'total_liquidations_7d' in metrics:
            message += f"\n• Liquidations (7d): ${metrics['total_liquidations_7d']:,.0f}"
    
    from .config import REGIME_RISK_MULTIPLIERS
    risk_mult = REGIME_RISK_MULTIPLIERS.get(new_regime, 0.8)
    message += f"\n\n*Risk Multiplier:* {risk_mult}x"
    
    # Determine severity based on regime
    if new_regime in ['STRESS', 'FRAGILE']:
        severity = 'CRITICAL'
    elif new_regime in ['TRANSITIONAL']:
        severity = 'WARNING'
    else:
        severity = 'INFO'
    
    return send_strategic_alert(message, severity)


def send_protocol_alerts(alerts: list) -> bool:
    """
    Send protocol health alerts to Slack.
    
    Args:
        alerts: List of alert strings from check_protocol_health()
    """
    if not alerts:
        return True
    
    message = "*Protocol Health Alerts*\n\n" + "\n".join(alerts)
    
    # Check severity level
    if any('CRITICAL' in a for a in alerts):
        severity = 'CRITICAL'
    else:
        severity = 'WARNING'
    
    return send_strategic_alert(message, severity)


def send_error_alert(error_message: str, component: str = 'Unknown') -> bool:
    """
    Send error alert for system failures.
    
    Args:
        error_message: Error description
        component: Which component failed
    """
    message = f"*System Error in {component}*\n\n```{error_message}```"
    return send_strategic_alert(message, 'CRITICAL')
