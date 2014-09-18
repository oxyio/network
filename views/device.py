# Oxypanel Network
# File: views/device.py
# Desc: special device views

from flask import url_for

from util.response import redirect_or_jsonify


# Edit device SSH details
def device_ssh(device):
    # For errors
    redirect_url = url_for('view_edit_object',
        module_name='network',
        object_type='device',
        object_id=device.id
    )

    # Apply & check SSH (as if new device)
    status, error = device.is_valid(new=True)
    if not status:
        return redirect_or_jsonify(redirect_url, error=error)

    # Update other details & save
    device.save()

    return redirect_or_jsonify(redirect_url, success='SSH details updated')

# Run a config'd command on a device
def device_command(device):
    pass
