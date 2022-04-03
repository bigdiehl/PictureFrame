from flask import Flask, url_for, render_template, redirect, request
from forms import ContactForm


app = Flask(__name__, instance_relative_config=False)

# Pulls configuration values from config.py
app.config.from_object('config')


@app.route('/', methods=('GET', 'POST'))
def contact():
    
    form = ContactForm()
    if form.validate_on_submit():
        return redirect(url_for('success'))
    return render_template(
        'index.html',
        form=form
    )


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
