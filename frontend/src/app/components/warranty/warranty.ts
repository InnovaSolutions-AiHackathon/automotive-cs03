import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../services/api.service';

@Component({
  selector: 'app-warranty',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './warranty.html',
  styleUrl: './warranty.scss',
})
export class Warranty implements OnInit {
  vehicles: any[] = [];
  warranties: any[] = [];
  selectedVehicleCode = '';
  repairType = 'engine';
  checkResult: any = null;
  loading = false;
  loadingWarranties = false;
  error = '';

  repairTypes = [
    'engine', 'transmission', 'drivetrain', 'electrical',
    'brakes', 'suspension', 'ac', 'interior',
    'catalytic_converter', 'o2_sensor'
  ];

  constructor(private api: ApiService) {}

  ngOnInit(): void {
    this.api.listVehicles().subscribe({
      next: (list) => (this.vehicles = list),
      error: () => (this.error = 'Failed to load vehicles'),
    });
  }

  onVehicleChange(): void {
    if (!this.selectedVehicleCode) return;
    this.loadingWarranties = true;
    this.warranties = [];
    this.checkResult = null;
    this.api.getVehicleWarranties(this.selectedVehicleCode).subscribe({
      next: (res) => {
        this.warranties = res.warranties ?? [];
        this.loadingWarranties = false;
      },
      error: () => {
        this.loadingWarranties = false;
      },
    });
  }

  checkCoverage(): void {
    if (!this.selectedVehicleCode) return;
    this.loading = true;
    this.checkResult = null;
    this.api.checkWarranty(this.selectedVehicleCode, this.repairType).subscribe({
      next: (res) => {
        this.checkResult = res;
        this.loading = false;
      },
      error: () => {
        this.error = 'Warranty check failed';
        this.loading = false;
      },
    });
  }
}
