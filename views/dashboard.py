from flask import render_template, g

from util.user import login_required


@login_required
def dashboard():
    g.module = 'network'
    g.module_color = 'purple'
    return render_template('network_dashboard.html')
