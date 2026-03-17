import { Component } from '@angular/core';
import { RouterModule } from '@angular/router';   // ✅ important
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth.service';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule, RouterModule], // ✅ add this
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.scss'],
})
export class LoginComponent {

  email: string = '';
  password: string = '';
  error = '';

  constructor(private router: Router, private auth : AuthService) {}

  async login() {

    if (!this.email || !this.password) {
      this.error = 'Email and Password required';
      return;
    }

    try {
      const data={
        email:this.email,
        password:this.password
      }

    this.auth.login(data).subscribe(res=>{
      this.auth.saveToken(res.access_token);
      this.router.navigate(['/home']);
    })

    } catch (e) {
      this.error = 'Invalid email or password';
    }
  }
}