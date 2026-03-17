import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';   // ✅ important

import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule],
  templateUrl: './signup.component.html',
  styleUrls: ['./signup.component.scss']
})
export class SignupComponent {
  
firstName: string = "";
lastName: string = "";
email: string = "";
mobile: string = "";
password: string = "";
confirm: string = "";
confirmMismatch: boolean = false;
apiError = '';
error = '';


  constructor(private router: Router, private auth : AuthService) {}

  async signup(form: any) {
      if (form.invalid) {
      return;
      }

    if (this.password !== this.confirm) {
      this.confirmMismatch = true;
      return;
    }

    const body = {
      first_name: this.firstName,
      last_name: this.lastName,
      email: this.email,
      password: this.password,
      mobile: this.mobile
    };

    try {
      this.auth.signup(body).subscribe({
        next: (response) => {
          console.log('Signup successful', response);
          this.router.navigate(['']);
        },
        error: (err) => {
          this.error = err?.error?.detail || 'Signup failed. Try again.';
        }
      });
    } catch (e) {
      this.error = 'Signup failed. Try again.';
    }
  }
}
