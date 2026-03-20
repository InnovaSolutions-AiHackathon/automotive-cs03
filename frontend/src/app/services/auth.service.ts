import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private baseUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  login(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/user/login`, data);
  }

  signup(data: any): Observable<any> {
    return this.http.post(`${this.baseUrl}/api/user/signup`, data);
  }

  saveToken(token: string): void {
    localStorage.setItem('token', token);
  }

  getToken(): string | null {
    return localStorage.getItem('token');
  }

  logout(): void {
    localStorage.removeItem('token');
    localStorage.removeItem('user');
  }

  /** Decode JWT payload and return user id (sub claim). */
  getUserId(): string | null {
    const token = this.getToken();
    if (!token) return null;
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.sub ?? payload.id ?? null;
    } catch {
      return null;
    }
  }

  /** Decode JWT payload and return user's first name. */
  getUserName(): string {
    const token = this.getToken();
    if (!token) return 'Agent';
    try {
      const payload = JSON.parse(atob(token.split('.')[1]));
      return payload.first_name ?? 'Agent';
    } catch {
      return 'Agent';
    }
  }

  isLoggedIn(): boolean {
    return !!this.getToken();
  }
}
